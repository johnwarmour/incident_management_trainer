"""Checkpoint scoring and debrief aggregation."""

from __future__ import annotations

from ..models.schemas import (
    Checkpoint,
    CheckpointScore,
    DebriefReport,
    SessionState,
)


def build_checkpoint_score(
    checkpoint: Checkpoint,
    raw: dict,
) -> CheckpointScore:
    """Build a CheckpointScore from the raw dict returned by Claude evaluation."""
    return CheckpointScore(
        checkpoint=checkpoint,
        score=max(0, min(100, int(raw.get("score", 50)))),
        max_score=100,
        feedback=raw.get("feedback", ""),
        missed_items=raw.get("missed_items", []),
        good_decisions=raw.get("good_decisions", []),
    )


def build_debrief(state: SessionState, overall_feedback: str) -> DebriefReport:
    """Aggregate all checkpoint scores into a final debrief report."""
    scores = state.scores
    total = sum(s.score for s in scores)
    overall = total // max(len(scores), 1)

    return DebriefReport(
        session_id=state.session_id,
        scenario_title=state.scenario_title,
        scenario_type=state.scenario_type,
        scores=scores,
        overall_score=overall,
        overall_feedback=overall_feedback,
        total_possible=len(scores) * 100,
    )
