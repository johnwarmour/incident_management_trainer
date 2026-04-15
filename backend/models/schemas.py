"""Pydantic models for incident simulation session state."""

from __future__ import annotations

from enum import Enum
from typing import Any, Union
from uuid import uuid4

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Checkpoint(str, Enum):
    DETECTION = "detection"
    TRIAGE = "triage"
    ESCALATION = "escalation"
    COMMUNICATION = "communication"
    RESOLUTION = "resolution"
    CLOSURE = "closure"


CHECKPOINT_ORDER = [
    Checkpoint.DETECTION,
    Checkpoint.TRIAGE,
    Checkpoint.ESCALATION,
    Checkpoint.COMMUNICATION,
    Checkpoint.RESOLUTION,
    Checkpoint.CLOSURE,
]


class Priority(str, Enum):
    P1 = "P1"  # Critical
    P2 = "P2"  # High
    P3 = "P3"  # Medium
    P4 = "P4"  # Low


class Impact(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Urgency(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ---------------------------------------------------------------------------
# Incident ticket
# ---------------------------------------------------------------------------

class IncidentTicket(BaseModel):
    """The live ITIL incident record, auto-populated as the user works."""

    inc_number: str = Field(default_factory=lambda: f"INC{uuid4().hex[:6].upper()}")
    title: str = ""
    description: str = ""
    category: str = ""
    affected_systems: list[str] = Field(default_factory=list)
    impact: Impact | None = None
    urgency: Urgency | None = None
    priority: Priority | None = None
    affected_users: str = ""
    workaround: str = ""
    resolution: str = ""
    escalation_contacts: list[str] = Field(default_factory=list)
    communication_sent: list[str] = Field(default_factory=list)
    status: str = "open"
    assigned_to: str = ""
    notes: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

class Role(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class ChatMessage(BaseModel):
    role: Role
    content: str
    checkpoint: Checkpoint | None = None


# ---------------------------------------------------------------------------
# Per-checkpoint data
# ---------------------------------------------------------------------------

class DetectionData(BaseModel):
    """Required fields for the DETECTION checkpoint."""
    alert_acknowledged: bool = False
    incident_logged: bool = False
    initial_description: str = ""


class TriageData(BaseModel):
    """Required fields for the TRIAGE checkpoint."""
    impact_assessed: Impact | None = None
    urgency_assessed: Urgency | None = None
    priority_set: Priority | None = None
    affected_users_estimated: str = ""


class EscalationData(BaseModel):
    """Required fields for the ESCALATION checkpoint."""
    escalation_decision: str = ""  # "escalate" | "handle" | "defer"
    escalation_targets: list[str] = Field(default_factory=list)
    escalation_reason: str = ""


class CommunicationData(BaseModel):
    """Required fields for the COMMUNICATION checkpoint."""
    stakeholders_notified: list[str] = Field(default_factory=list)
    communication_method: str = ""
    update_sent: str = ""
    next_update_scheduled: str = ""


class ResolutionData(BaseModel):
    """Required fields for the RESOLUTION checkpoint."""
    workaround_identified: bool = False
    workaround_description: str = ""
    fix_type: str = ""  # "workaround" | "permanent_fix" | "escalated"
    resolution_steps: str = ""


class ClosureData(BaseModel):
    """Required fields for the CLOSURE checkpoint."""
    incident_closed: bool = False
    pir_required: bool = False
    problem_record_raised: bool = False
    lessons_learned: str = ""
    closure_notes: str = ""


CheckpointData = Union[DetectionData, TriageData, EscalationData, CommunicationData, ResolutionData, ClosureData]


# ---------------------------------------------------------------------------
# Checkpoint score
# ---------------------------------------------------------------------------

class CheckpointScore(BaseModel):
    checkpoint: Checkpoint
    score: int = Field(ge=0, le=100)
    max_score: int = 100
    feedback: str
    missed_items: list[str] = Field(default_factory=list)
    good_decisions: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

class SessionState(BaseModel):
    """Complete state of a simulation session."""

    session_id: str = Field(default_factory=lambda: uuid4().hex)
    scenario_type: str = ""
    scenario_title: str = ""
    scenario_summary: str = ""  # brief description shown to user at start

    current_checkpoint: Checkpoint = Checkpoint.DETECTION
    completed_checkpoints: list[Checkpoint] = Field(default_factory=list)
    is_complete: bool = False

    ticket: IncidentTicket = Field(default_factory=IncidentTicket)

    # Full conversation history (for Claude API)
    conversation: list[ChatMessage] = Field(default_factory=list)

    # Per-checkpoint collected data
    detection: DetectionData = Field(default_factory=DetectionData)
    triage: TriageData = Field(default_factory=TriageData)
    escalation: EscalationData = Field(default_factory=EscalationData)
    communication: CommunicationData = Field(default_factory=CommunicationData)
    resolution: ResolutionData = Field(default_factory=ResolutionData)
    closure: ClosureData = Field(default_factory=ClosureData)

    # Scores (populated as checkpoints complete)
    scores: list[CheckpointScore] = Field(default_factory=list)

    # Hidden scenario context (not shown to user directly)
    scenario_context: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# API request/response models
# ---------------------------------------------------------------------------

class StartSessionRequest(BaseModel):
    scenario_type: str | None = None  # None = random


class StartSessionResponse(BaseModel):
    session_id: str
    scenario_title: str
    scenario_summary: str
    initial_message: str
    ticket: IncidentTicket
    current_checkpoint: Checkpoint


class UserInputRequest(BaseModel):
    message: str


class UserInputResponse(BaseModel):
    assistant_message: str
    ticket: IncidentTicket
    current_checkpoint: Checkpoint
    checkpoint_complete: bool
    checkpoint_score: CheckpointScore | None = None
    session_complete: bool = False


class SessionStateResponse(BaseModel):
    session_id: str
    scenario_title: str
    scenario_summary: str
    current_checkpoint: Checkpoint
    completed_checkpoints: list[Checkpoint]
    ticket: IncidentTicket
    conversation: list[ChatMessage]
    is_complete: bool


class DebriefReport(BaseModel):
    session_id: str
    scenario_title: str
    scenario_type: str
    scores: list[CheckpointScore]
    overall_score: int
    overall_feedback: str
    total_possible: int


class AdvanceCheckpointRequest(BaseModel):
    """Force advance past the current checkpoint (for testing / when user is stuck)."""
    pass
