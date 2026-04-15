import type { Checkpoint, CheckpointScore, IncidentTicket } from "../api";

interface Props {
  checkpoint: Checkpoint;
  ticket: IncidentTicket;
  completedCheckpoints: Checkpoint[];
  lastScore: CheckpointScore | null;
  onForceAdvance: () => void;
  loading: boolean;
  sessionComplete: boolean;
}

const CHECKPOINT_LABELS: Record<Checkpoint, string> = {
  detection: "Detection",
  triage: "Triage",
  escalation: "Escalation",
  communication: "Communication",
  resolution: "Resolution",
  closure: "Closure",
};

const CHECKPOINT_GOALS: Record<Checkpoint, string[]> = {
  detection: [
    "Acknowledge the alert",
    "Log the incident with a title",
    "Write an initial description",
    "Identify affected systems",
  ],
  triage: [
    "Assess impact (High / Medium / Low)",
    "Assess urgency (High / Medium / Low)",
    "Set priority using ITIL matrix",
    "Estimate number of affected users",
  ],
  escalation: [
    "Decide whether to escalate",
    "Identify the right contacts",
    "Notify them with context",
  ],
  communication: [
    "Identify affected stakeholders",
    "Send a clear, non-technical update",
    "Establish update cadence",
  ],
  resolution: [
    "Investigate root cause",
    "Identify a workaround",
    "Implement and verify the fix",
    "Update the incident record",
  ],
  closure: [
    "Formally close the incident",
    "Determine if PIR is needed (P1/P2)",
    "Raise problem record if recurring",
    "Capture lessons learned",
  ],
};

function scoreColor(score: number): string {
  if (score >= 80) return "#22c55e";
  if (score >= 60) return "#f59e0b";
  return "#ef4444";
}

export function CheckpointPanel({
  checkpoint,
  ticket,
  completedCheckpoints,
  lastScore,
  onForceAdvance,
  loading,
  sessionComplete,
}: Props) {
  const goals = CHECKPOINT_GOALS[checkpoint] ?? [];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16, height: "100%", overflow: "auto" }}>
      {/* Current checkpoint header */}
      <div>
        <div style={{ color: "#6b7280", fontSize: 10, letterSpacing: 1, textTransform: "uppercase", marginBottom: 4 }}>
          Current Step
        </div>
        <div style={{ color: "#f59e0b", fontSize: 18, fontWeight: 700, textTransform: "capitalize" }}>
          {CHECKPOINT_LABELS[checkpoint]}
        </div>
      </div>

      {/* Goals */}
      <div>
        <div style={{ color: "#6b7280", fontSize: 11, letterSpacing: 1, textTransform: "uppercase", marginBottom: 8 }}>
          Required Actions
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {goals.map((goal) => {
            const done = isGoalMet(goal, checkpoint, ticket, completedCheckpoints);
            return (
              <div key={goal} style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
                <span
                  style={{
                    width: 14,
                    height: 14,
                    borderRadius: 3,
                    border: `2px solid ${done ? "#22c55e" : "#4b5563"}`,
                    background: done ? "#22c55e" : "transparent",
                    flexShrink: 0,
                    marginTop: 2,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: 9,
                    color: "#fff",
                  }}
                >
                  {done ? "✓" : ""}
                </span>
                <span style={{ color: done ? "#4ade80" : "#9ca3af", fontSize: 13, lineHeight: 1.4 }}>
                  {goal}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Last score (shown after advancing) */}
      {lastScore && (
        <div
          style={{
            background: "#111827",
            border: "1px solid #374151",
            borderRadius: 8,
            padding: 12,
          }}
        >
          <div style={{ color: "#6b7280", fontSize: 11, letterSpacing: 1, textTransform: "uppercase", marginBottom: 8 }}>
            Previous Checkpoint Score
          </div>
          <div
            style={{
              fontSize: 28,
              fontWeight: 700,
              color: scoreColor(lastScore.score),
              marginBottom: 6,
            }}
          >
            {lastScore.score}
            <span style={{ fontSize: 14, color: "#6b7280" }}>/100</span>
          </div>
          <div style={{ color: "#d1d5db", fontSize: 12, lineHeight: 1.5, marginBottom: 8 }}>
            {lastScore.feedback}
          </div>
          {lastScore.good_decisions.length > 0 && (
            <div style={{ marginBottom: 6 }}>
              {lastScore.good_decisions.map((g) => (
                <div key={g} style={{ color: "#4ade80", fontSize: 11, display: "flex", gap: 4 }}>
                  <span>✓</span>
                  <span>{g}</span>
                </div>
              ))}
            </div>
          )}
          {lastScore.missed_items.length > 0 && (
            <div>
              {lastScore.missed_items.map((m) => (
                <div key={m} style={{ color: "#f87171", fontSize: 11, display: "flex", gap: 4 }}>
                  <span>✗</span>
                  <span>{m}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ITIL Quick reference */}
      <div
        style={{
          background: "#111827",
          border: "1px solid #1f2937",
          borderRadius: 6,
          padding: 10,
        }}
      >
        <div style={{ color: "#6b7280", fontSize: 11, letterSpacing: 1, textTransform: "uppercase", marginBottom: 6 }}>
          Priority Matrix
        </div>
        <table style={{ fontSize: 11, color: "#9ca3af", borderCollapse: "collapse", width: "100%" }}>
          <thead>
            <tr>
              <th style={thStyle}>Impact＼Urgency</th>
              <th style={{ ...thStyle, color: "#ef4444" }}>High</th>
              <th style={{ ...thStyle, color: "#f97316" }}>Med</th>
              <th style={{ ...thStyle, color: "#eab308" }}>Low</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td style={{ ...tdStyle, color: "#ef4444" }}>High</td>
              <td style={{ ...tdStyle, color: "#ef4444", fontWeight: 700 }}>P1</td>
              <td style={{ ...tdStyle, color: "#f97316", fontWeight: 700 }}>P2</td>
              <td style={{ ...tdStyle, color: "#eab308", fontWeight: 700 }}>P3</td>
            </tr>
            <tr>
              <td style={{ ...tdStyle, color: "#f97316" }}>Medium</td>
              <td style={{ ...tdStyle, color: "#f97316", fontWeight: 700 }}>P2</td>
              <td style={{ ...tdStyle, color: "#eab308", fontWeight: 700 }}>P3</td>
              <td style={{ ...tdStyle, color: "#22c55e", fontWeight: 700 }}>P4</td>
            </tr>
            <tr>
              <td style={{ ...tdStyle, color: "#eab308" }}>Low</td>
              <td style={{ ...tdStyle, color: "#eab308", fontWeight: 700 }}>P3</td>
              <td style={{ ...tdStyle, color: "#22c55e", fontWeight: 700 }}>P4</td>
              <td style={{ ...tdStyle, color: "#22c55e", fontWeight: 700 }}>P4</td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Force advance button */}
      {!sessionComplete && (
        <button
          onClick={onForceAdvance}
          disabled={loading}
          style={{
            background: "transparent",
            border: "1px solid #4b5563",
            color: "#9ca3af",
            borderRadius: 6,
            padding: "6px 12px",
            cursor: loading ? "not-allowed" : "pointer",
            fontSize: 12,
            marginTop: "auto",
          }}
        >
          Skip checkpoint →
        </button>
      )}
    </div>
  );
}

const thStyle: React.CSSProperties = {
  padding: "3px 6px",
  textAlign: "center",
  fontWeight: 600,
  color: "#6b7280",
  fontSize: 10,
};

const tdStyle: React.CSSProperties = {
  padding: "3px 6px",
  textAlign: "center",
  borderTop: "1px solid #1f2937",
};

/** Best-effort check whether a goal is satisfied based on ticket state. */
function isGoalMet(
  goal: string,
  checkpoint: Checkpoint,
  ticket: IncidentTicket,
  completed: Checkpoint[],
): boolean {
  if (completed.includes(checkpoint)) return true;
  const g = goal.toLowerCase();

  if (g.includes("title") || g.includes("acknowledge") || g.includes("log the incident")) {
    return Boolean(ticket.title);
  }
  if (g.includes("description")) return Boolean(ticket.description);
  if (g.includes("affected systems")) return ticket.affected_systems.length > 0;
  if (g.includes("impact")) return Boolean(ticket.impact);
  if (g.includes("urgency")) return Boolean(ticket.urgency);
  if (g.includes("priority")) return Boolean(ticket.priority);
  if (g.includes("affected users")) return Boolean(ticket.affected_users);
  if (g.includes("escalat")) return ticket.escalation_contacts.length > 0;
  if (g.includes("stakeholder") || g.includes("communication")) {
    return ticket.communication_sent.length > 0;
  }
  if (g.includes("workaround")) return Boolean(ticket.workaround);
  if (g.includes("close")) return ticket.status === "closed";

  return false;
}
