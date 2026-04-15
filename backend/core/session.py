"""Session state machine — ITIL checkpoint progression."""

from __future__ import annotations

from typing import Any

from ..models.schemas import (
    CHECKPOINT_ORDER,
    Checkpoint,
    ChatMessage,
    CheckpointScore,
    IncidentTicket,
    Priority,
    Role,
    SessionState,
    TriageData,
)


def next_checkpoint(current: Checkpoint) -> Checkpoint | None:
    """Return the next checkpoint, or None if we're at CLOSURE."""
    idx = CHECKPOINT_ORDER.index(current)
    if idx + 1 >= len(CHECKPOINT_ORDER):
        return None
    return CHECKPOINT_ORDER[idx + 1]


def checkpoint_is_ready(state: SessionState) -> bool:
    """
    Check whether the current checkpoint has the minimum required data
    to be advanced. The Claude model signals readiness via a "Checkpoint complete"
    marker in its response, but this provides a programmatic fallback.
    """
    cp = state.current_checkpoint
    ticket = state.ticket

    if cp == Checkpoint.DETECTION:
        return bool(ticket.title and ticket.description)

    if cp == Checkpoint.TRIAGE:
        return (
            ticket.impact is not None
            and ticket.urgency is not None
            and ticket.priority is not None
        )

    if cp == Checkpoint.ESCALATION:
        return bool(state.escalation.escalation_decision)

    if cp == Checkpoint.COMMUNICATION:
        return len(ticket.communication_sent) > 0

    if cp == Checkpoint.RESOLUTION:
        return bool(ticket.workaround or ticket.resolution)

    if cp == Checkpoint.CLOSURE:
        return bool(ticket.status == "closed")

    return False


def apply_ticket_updates(state: SessionState, updates: dict[str, Any]) -> None:
    """Apply a dict of ticket field updates to the session ticket."""
    ticket_data = state.ticket.model_dump()
    ticket_data.update(updates)
    state.ticket = IncidentTicket(**ticket_data)


def extract_ticket_updates_from_text(text: str) -> dict[str, Any]:
    """
    Heuristic extraction of ticket field updates from user message text.
    Looks for structured patterns the user might type.
    This is a best-effort helper; Claude drives the narrative.
    """
    updates: dict[str, Any] = {}
    lower = text.lower()

    # Priority detection
    for p in ["p1", "p2", "p3", "p4"]:
        if p in lower:
            updates["priority"] = Priority(p.upper())
            break

    # Impact
    if "high impact" in lower or "impact: high" in lower:
        from ..models.schemas import Impact
        updates["impact"] = Impact.HIGH
    elif "medium impact" in lower or "impact: medium" in lower:
        from ..models.schemas import Impact
        updates["impact"] = Impact.MEDIUM
    elif "low impact" in lower or "impact: low" in lower:
        from ..models.schemas import Impact
        updates["impact"] = Impact.LOW

    # Urgency
    if "high urgency" in lower or "urgency: high" in lower:
        from ..models.schemas import Urgency
        updates["urgency"] = Urgency.HIGH
    elif "medium urgency" in lower or "urgency: medium" in lower:
        from ..models.schemas import Urgency
        updates["urgency"] = Urgency.MEDIUM
    elif "low urgency" in lower or "urgency: low" in lower:
        from ..models.schemas import Urgency
        updates["urgency"] = Urgency.LOW

    # Closure
    if "close incident" in lower or "closing incident" in lower:
        updates["status"] = "closed"

    return updates


def add_message(state: SessionState, role: Role, content: str) -> None:
    """Append a message to the session conversation."""
    state.conversation.append(
        ChatMessage(role=role, content=content, checkpoint=state.current_checkpoint)
    )


def advance_checkpoint(state: SessionState, score: CheckpointScore) -> bool:
    """
    Mark current checkpoint complete, record score, advance to next.
    Returns True if the session is now complete (CLOSURE done).
    """
    state.completed_checkpoints.append(state.current_checkpoint)
    state.scores.append(score)

    nxt = next_checkpoint(state.current_checkpoint)
    if nxt is None:
        state.is_complete = True
        return True

    state.current_checkpoint = nxt
    return False


def detect_checkpoint_complete_signal(assistant_message: str) -> bool:
    """
    Detect if Claude signalled checkpoint completion in its response.
    Claude is instructed to say "Checkpoint complete" when ready.
    """
    lower = assistant_message.lower()
    return "checkpoint complete" in lower


def get_checkpoint_conversation(state: SessionState, checkpoint: Checkpoint) -> list[ChatMessage]:
    """Return only the messages that occurred during the given checkpoint."""
    return [m for m in state.conversation if m.checkpoint == checkpoint]
