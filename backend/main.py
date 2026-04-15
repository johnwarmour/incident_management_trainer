"""FastAPI backend for the ITIL Incident Simulation Training Environment."""

from __future__ import annotations

import os
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .core import (
    ClaudeClient,
    add_message,
    advance_checkpoint,
    build_checkpoint_score,
    build_debrief,
    detect_checkpoint_complete_signal,
    extract_ticket_updates_from_text,
    get_checkpoint_conversation,
    get_template,
    pick_scenario_type,
)
from .models.schemas import (
    AdvanceCheckpointRequest,
    DebriefReport,
    Role,
    SessionState,
    SessionStateResponse,
    StartSessionRequest,
    StartSessionResponse,
    UserInputRequest,
    UserInputResponse,
)

load_dotenv()

app = FastAPI(title="Incident Sim API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session store (replace with SQLite for persistence)
_sessions: dict[str, SessionState] = {}
_claude = ClaudeClient()


# ---------------------------------------------------------------------------
# Session lifecycle
# ---------------------------------------------------------------------------

@app.post("/session/start", response_model=StartSessionResponse)
async def start_session(req: StartSessionRequest) -> StartSessionResponse:
    """Create a new simulation session with an AI-generated scenario."""
    scenario_type = pick_scenario_type(req.scenario_type)
    template = get_template(scenario_type)

    # Generate scenario via Claude
    scenario_ctx = _claude.generate_scenario(scenario_type, template)

    state = SessionState(
        scenario_type=scenario_type,
        scenario_title=scenario_ctx["title"],
        scenario_summary=scenario_ctx["summary"],
        scenario_context=scenario_ctx,
    )

    # Prime the ticket with known info
    state.ticket.title = scenario_ctx["title"]
    state.ticket.affected_systems = scenario_ctx.get("affected_systems", [])

    # Generate the opening dispatcher message
    opening_prompt = (
        f"[SIMULATION START]\n"
        f"Alert received: {scenario_ctx.get('alert_text', 'Critical alert triggered.')}\n\n"
        f"You have just been paged as the incident manager on call. The simulation has begun. "
        f"Introduce yourself as the monitoring system and present the initial alert. "
        f"Be realistic — paste the alert text, mention the time, and wait for the trainee to respond."
    )

    assistant_opening = _claude.chat(state, opening_prompt)

    # Add only the assistant opening to history (the opening prompt is synthetic)
    add_message(state, Role.ASSISTANT, assistant_opening)

    _sessions[state.session_id] = state

    return StartSessionResponse(
        session_id=state.session_id,
        scenario_title=state.scenario_title,
        scenario_summary=state.scenario_summary,
        initial_message=assistant_opening,
        ticket=state.ticket,
        current_checkpoint=state.current_checkpoint,
    )


@app.post("/session/{session_id}/input", response_model=UserInputResponse)
async def session_input(session_id: str, req: UserInputRequest) -> UserInputResponse:
    """Process a user message and return the assistant response."""
    state = _sessions.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")
    if state.is_complete:
        raise HTTPException(status_code=400, detail="Session is already complete")

    # Record user message
    add_message(state, Role.USER, req.message)

    # Apply any ticket updates heuristically detected from the user message
    updates = extract_ticket_updates_from_text(req.message)
    if updates:
        from .core.session import apply_ticket_updates
        apply_ticket_updates(state, updates)

    # Get Claude response
    assistant_msg = _claude.chat(state, req.message)
    add_message(state, Role.ASSISTANT, assistant_msg)

    # Check if Claude signalled checkpoint completion
    checkpoint_complete = detect_checkpoint_complete_signal(assistant_msg)
    checkpoint_score = None
    session_complete = False

    if checkpoint_complete:
        # Evaluate the checkpoint
        cp_conv = get_checkpoint_conversation(state, state.current_checkpoint)
        raw_eval = _claude.evaluate_checkpoint(state, state.current_checkpoint, cp_conv)
        checkpoint_score = build_checkpoint_score(state.current_checkpoint, raw_eval)

        # Advance the state machine
        session_complete = advance_checkpoint(state, checkpoint_score)

        if session_complete:
            # Generate overall debrief
            overall_feedback = _claude.generate_debrief(state)
            # Store debrief on the state for retrieval
            state.scenario_context["debrief_feedback"] = overall_feedback

    return UserInputResponse(
        assistant_message=assistant_msg,
        ticket=state.ticket,
        current_checkpoint=state.current_checkpoint,
        checkpoint_complete=checkpoint_complete,
        checkpoint_score=checkpoint_score,
        session_complete=session_complete,
    )


@app.get("/session/{session_id}", response_model=SessionStateResponse)
async def get_session(session_id: str) -> SessionStateResponse:
    """Get the current state of a session."""
    state = _sessions.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionStateResponse(
        session_id=state.session_id,
        scenario_title=state.scenario_title,
        scenario_summary=state.scenario_summary,
        current_checkpoint=state.current_checkpoint,
        completed_checkpoints=state.completed_checkpoints,
        ticket=state.ticket,
        conversation=state.conversation,
        is_complete=state.is_complete,
    )


@app.post("/session/{session_id}/advance", response_model=UserInputResponse)
async def force_advance(session_id: str, req: AdvanceCheckpointRequest) -> UserInputResponse:
    """
    Force advance past the current checkpoint (for when the user is stuck
    or wants to skip ahead). Evaluates current state and advances.
    """
    state = _sessions.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")
    if state.is_complete:
        raise HTTPException(status_code=400, detail="Session is already complete")

    cp_conv = get_checkpoint_conversation(state, state.current_checkpoint)
    raw_eval = _claude.evaluate_checkpoint(state, state.current_checkpoint, cp_conv)
    checkpoint_score = build_checkpoint_score(state.current_checkpoint, raw_eval)

    session_complete = advance_checkpoint(state, checkpoint_score)
    if session_complete:
        overall_feedback = _claude.generate_debrief(state)
        state.scenario_context["debrief_feedback"] = overall_feedback

    transition_msg = (
        f"[Checkpoint {state.completed_checkpoints[-1].value.upper()} complete — "
        f"moving to {state.current_checkpoint.value.upper()}]\n\n"
        + (
            f"Session complete! Check your debrief."
            if session_complete
            else f"Now let's focus on {state.current_checkpoint.value.upper()}."
        )
    )
    add_message(state, Role.ASSISTANT, transition_msg)

    return UserInputResponse(
        assistant_message=transition_msg,
        ticket=state.ticket,
        current_checkpoint=state.current_checkpoint,
        checkpoint_complete=True,
        checkpoint_score=checkpoint_score,
        session_complete=session_complete,
    )


@app.get("/session/{session_id}/debrief", response_model=DebriefReport)
async def get_debrief(session_id: str) -> DebriefReport:
    """Get the final debrief report for a completed session."""
    state = _sessions.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")
    if not state.is_complete:
        raise HTTPException(status_code=400, detail="Session is not yet complete")

    overall_feedback = state.scenario_context.get("debrief_feedback", "Session complete.")
    return build_debrief(state, overall_feedback)


@app.get("/scenarios")
async def list_scenarios() -> dict:
    """List available scenario types."""
    from .core.scenario import SCENARIO_TEMPLATES
    return {
        "scenarios": [
            {"type": k, "description": v["description"]}
            for k, v in SCENARIO_TEMPLATES.items()
        ]
    }


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Static frontend (served in production)
# ---------------------------------------------------------------------------

_frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if _frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="frontend")


def main() -> None:
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
