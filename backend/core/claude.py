"""Anthropic SDK client with prompt caching for multi-turn incident sessions."""

from __future__ import annotations

import os
from typing import Any

import anthropic

from ..models.schemas import (
    ChatMessage,
    Checkpoint,
    Role,
    SessionState,
)

MODEL = "claude-opus-4-6"

# The ITIL rules injected into every session (stable prefix — cached)
ITIL_SYSTEM_PROMPT = """You are running an ITIL incident management simulation for a training session.

## Your Role
You play three characters simultaneously, switching fluidly based on what makes sense:

1. **MONITORING SYSTEM / DISPATCHER** — You surface alert details, logs, metrics, and new information as time progresses. When the trainee asks "what do the logs show?" or "check the dashboards", respond as the monitoring system with realistic technical data.

2. **STAKEHOLDERS** — You play various affected parties: the CTO demanding updates, the customer success team reporting user complaints, the business owner asking for ETAs, the on-call engineer who first noticed the issue.

3. **NARRATOR** — When the trainee makes a decision, you advance the scenario realistically. If they escalate, the on-call engineer picks up. If they send a stakeholder update, you confirm receipt and may ask follow-up questions.

## ITIL Framework You Enforce
The simulation follows six structured checkpoints:
- **DETECTION**: Alert acknowledged, incident logged with initial description
- **TRIAGE**: Impact/urgency assessed, priority matrix applied (P1=critical/critical, P2=high/medium or medium/high, P3=medium/medium, P4=low/*)
- **ESCALATION**: Decision to escalate or handle, appropriate contacts notified
- **COMMUNICATION**: Stakeholders informed, update cadence established
- **RESOLUTION**: Workaround or fix identified and implemented
- **CLOSURE**: Incident closed, PIR triggered if P1/P2, problem record if recurring

## Priority Matrix
| Impact \ Urgency | High | Medium | Low |
|------------------|------|--------|-----|
| High             | P1   | P2     | P3  |
| Medium           | P2   | P3     | P4  |
| Low              | P3   | P4     | P4  |

## Simulation Rules
- Stay in character. Don't break the fourth wall or explain what the trainee "should" do — let them make decisions.
- Surface information gradually. Don't dump everything at once. The trainee should have to ask the right questions.
- React realistically to bad decisions. If they escalate a P4 to the CTO, the CTO is annoyed. If they miss communication, stakeholders escalate to you.
- When the trainee has completed the required actions for the current checkpoint, you may tell them "Checkpoint complete — [brief summary of what they did well or missed]" to signal readiness to advance.
- Keep responses concise and realistic. One or two paragraphs max unless presenting logs/data.

## Current Checkpoint Guidance
You will be told the current checkpoint at the start of each turn. Gently guide the conversation toward completing that checkpoint's requirements without being heavy-handed."""

# Per-checkpoint system addendum (injected as a reminder, not cached)
CHECKPOINT_GUIDANCE: dict[Checkpoint, str] = {
    Checkpoint.DETECTION: (
        "CURRENT CHECKPOINT: DETECTION\n"
        "The trainee needs to: (1) acknowledge the alert, (2) create an initial incident record with title and description. "
        "Help them understand what's happening but don't give away too much. Wait for them to ask questions."
    ),
    Checkpoint.TRIAGE: (
        "CURRENT CHECKPOINT: TRIAGE\n"
        "The trainee needs to: (1) assess impact (how many users/systems affected?), "
        "(2) assess urgency (how time-sensitive?), (3) set priority using the ITIL matrix. "
        "If they set the wrong priority, challenge them — ask 'Are you sure? How many customers are affected?'"
    ),
    Checkpoint.ESCALATION: (
        "CURRENT CHECKPOINT: ESCALATION\n"
        "The trainee needs to: decide whether to escalate and to whom. "
        "For P1/P2, escalation is expected. For P3/P4, they may handle it themselves. "
        "If they don't escalate a P1, play an impatient stakeholder asking why the CTO isn't aware."
    ),
    Checkpoint.COMMUNICATION: (
        "CURRENT CHECKPOINT: COMMUNICATION\n"
        "The trainee needs to: notify affected stakeholders with an update. "
        "For P1: update within 15 min, then every 30 min. For P2: update within 30 min. "
        "If they send a vague update, play the CTO asking for more specifics."
    ),
    Checkpoint.RESOLUTION: (
        "CURRENT CHECKPOINT: RESOLUTION\n"
        "The trainee needs to: identify and implement a workaround or fix. "
        "You know the root cause — surface clues in logs/metrics as they investigate. "
        "Confirm when the fix/workaround is applied and whether monitoring shows recovery."
    ),
    Checkpoint.CLOSURE: (
        "CURRENT CHECKPOINT: CLOSURE\n"
        "The trainee needs to: close the incident, determine if a PIR is needed (P1/P2 = yes), "
        "and decide if a problem record should be raised (recurring issues). "
        "Ask about lessons learned and what they'd do differently."
    ),
}


class ClaudeClient:
    """Manages Claude API calls for a simulation session with prompt caching."""

    def __init__(self) -> None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY environment variable not set")
        self._client = anthropic.Anthropic(api_key=api_key)

    def generate_scenario(self, scenario_type: str, template: dict[str, Any]) -> dict[str, Any]:
        """
        Expand a scenario seed template into a full incident scenario.
        Returns a dict with: title, summary, alert_text, affected_systems,
        root_cause (hidden), initial_impact, initial_urgency, clues.
        """
        prompt = f"""You are generating a realistic IT incident scenario for an ITIL training simulation.

Scenario type: {scenario_type}
Template context: {template}

Generate a complete incident scenario as a JSON object with these exact fields:
{{
  "title": "brief incident title (e.g. 'Database primary node unresponsive')",
  "summary": "one sentence the trainee sees at the start",
  "alert_text": "realistic monitoring alert text that triggered the incident (2-4 lines)",
  "affected_systems": ["list", "of", "system names"],
  "business_impact": "what business capability is affected",
  "initial_symptoms": "what the monitoring shows at T+0",
  "root_cause": "the actual root cause (hidden from trainee, revealed through investigation)",
  "clues_in_logs": ["clue 1 visible in logs", "clue 2 visible in metrics", "clue 3 from recent changes"],
  "true_impact": "high|medium|low",
  "true_urgency": "high|medium|low",
  "true_priority": "P1|P2|P3|P4",
  "stakeholders": ["name: role", "name: role"],
  "workaround": "the workaround that works",
  "permanent_fix": "the permanent fix required"
}}

Return ONLY valid JSON, no markdown fences."""

        response = self._client.messages.create(
            model=MODEL,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )

        import json
        text = response.content[0].text.strip()
        # Strip markdown fences if model added them anyway
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            text = text.rsplit("```", 1)[0]
        return json.loads(text)

    def chat(self, state: SessionState, user_message: str) -> str:
        """
        Send a user message and get an assistant response.
        Uses prompt caching: the stable system prompt + scenario context are cached.
        """
        # Build the cached system prompt
        scenario_info = (
            f"\n\n## SCENARIO CONTEXT (confidential — you know this, trainee does not)\n"
            f"Title: {state.scenario_title}\n"
            f"Root cause: {state.scenario_context.get('root_cause', 'unknown')}\n"
            f"Clues in logs: {state.scenario_context.get('clues_in_logs', [])}\n"
            f"True priority: {state.scenario_context.get('true_priority', 'unknown')}\n"
            f"Workaround: {state.scenario_context.get('workaround', 'unknown')}\n"
            f"Stakeholders: {state.scenario_context.get('stakeholders', [])}\n"
            f"Business impact: {state.scenario_context.get('business_impact', 'unknown')}\n"
        )

        # Stable system block (cached) — ITIL rules + scenario context
        system = [
            {
                "type": "text",
                "text": ITIL_SYSTEM_PROMPT + scenario_info,
                "cache_control": {"type": "ephemeral"},
            }
        ]

        # Build messages from conversation history
        messages: list[dict] = []
        for msg in state.conversation:
            messages.append({"role": msg.role.value, "content": msg.content})

        # Append the new user message with checkpoint guidance
        checkpoint_hint = CHECKPOINT_GUIDANCE.get(state.current_checkpoint, "")
        full_user_message = f"[{checkpoint_hint}]\n\n{user_message}" if checkpoint_hint else user_message
        messages.append({"role": "user", "content": full_user_message})

        response = self._client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=system,
            messages=messages,
        )

        return response.content[0].text

    def evaluate_checkpoint(
        self,
        state: SessionState,
        checkpoint: Checkpoint,
        conversation_excerpt: list[ChatMessage],
    ) -> dict[str, Any]:
        """
        Evaluate the trainee's performance at a completed checkpoint.
        Returns: {"score": int, "feedback": str, "missed_items": list, "good_decisions": list}
        """
        conv_text = "\n".join(
            f"{m.role.value.upper()}: {m.content}"
            for m in conversation_excerpt
        )

        criteria = {
            Checkpoint.DETECTION: [
                "Acknowledged the alert promptly",
                "Created an incident record with title and description",
                "Identified affected systems",
                "Set initial category",
            ],
            Checkpoint.TRIAGE: [
                f"Correctly assessed impact as {state.scenario_context.get('true_impact', 'unknown')}",
                f"Correctly assessed urgency as {state.scenario_context.get('true_urgency', 'unknown')}",
                f"Set correct priority ({state.scenario_context.get('true_priority', 'unknown')})",
                "Estimated affected user count",
            ],
            Checkpoint.ESCALATION: [
                "Made an appropriate escalation decision",
                "Contacted the right people (management, technical leads, or SMEs)",
                "Provided context when escalating",
            ],
            Checkpoint.COMMUNICATION: [
                "Notified affected stakeholders",
                "Communication was clear and specific",
                "Established update cadence",
                "Avoided jargon in stakeholder updates",
            ],
            Checkpoint.RESOLUTION: [
                "Investigated root cause systematically",
                "Identified a workaround or fix",
                "Verified the fix worked",
                "Updated the incident record",
            ],
            Checkpoint.CLOSURE: [
                "Formally closed the incident",
                "Determined PIR need correctly (P1/P2 require PIR)",
                "Considered whether a problem record is needed",
                "Captured lessons learned",
            ],
        }

        prompt = f"""You are evaluating an ITIL incident management trainee's performance at the {checkpoint.value.upper()} checkpoint.

Scenario: {state.scenario_title}
True priority: {state.scenario_context.get('true_priority', 'unknown')}
True impact: {state.scenario_context.get('true_impact', 'unknown')}
True urgency: {state.scenario_context.get('true_urgency', 'unknown')}

Evaluation criteria for this checkpoint:
{chr(10).join(f'- {c}' for c in criteria.get(checkpoint, []))}

Conversation at this checkpoint:
{conv_text}

Trainee's ticket state:
- Impact: {state.ticket.impact}
- Urgency: {state.ticket.urgency}
- Priority: {state.ticket.priority}
- Escalation contacts: {state.ticket.escalation_contacts}
- Workaround: {state.ticket.workaround}

Evaluate and return JSON with this exact structure:
{{
  "score": <integer 0-100>,
  "feedback": "<one paragraph of constructive feedback>",
  "missed_items": ["<thing they missed or did wrong>"],
  "good_decisions": ["<thing they did well>"]
}}

Return ONLY valid JSON."""

        response = self._client.messages.create(
            model=MODEL,
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )

        import json
        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            text = text.rsplit("```", 1)[0]
        return json.loads(text)

    def generate_debrief(self, state: SessionState) -> str:
        """Generate overall debrief summary after session completion."""
        scores_summary = "\n".join(
            f"- {s.checkpoint.value}: {s.score}/100 — {s.feedback}"
            for s in state.scores
        )
        overall = sum(s.score for s in state.scores) // max(len(state.scores), 1)

        prompt = f"""Write a brief (3-4 paragraph) overall debrief for an ITIL incident management trainee.

Scenario: {state.scenario_title} ({state.scenario_type})
Overall score: {overall}/100

Per-checkpoint performance:
{scores_summary}

Focus on:
1. Their strongest area
2. Their weakest area and why it matters in real incidents
3. One specific ITIL concept they should review
4. An encouraging closing note

Keep it under 300 words."""

        response = self._client.messages.create(
            model=MODEL,
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
