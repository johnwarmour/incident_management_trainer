import type { IncidentTicket, Checkpoint } from "../api";

interface Props {
  ticket: IncidentTicket;
  currentCheckpoint: Checkpoint;
  completedCheckpoints: Checkpoint[];
}

const PRIORITY_COLOR: Record<string, string> = {
  P1: "#ef4444",
  P2: "#f97316",
  P3: "#eab308",
  P4: "#22c55e",
};

const CHECKPOINTS: Checkpoint[] = [
  "detection",
  "triage",
  "escalation",
  "communication",
  "resolution",
  "closure",
];

function Badge({ label, value, color }: { label: string; value: string; color?: string }) {
  if (!value) return null;
  return (
    <div style={{ display: "flex", gap: 6, alignItems: "center", marginBottom: 4 }}>
      <span style={{ color: "#9ca3af", fontSize: 11, minWidth: 90 }}>{label}</span>
      <span
        style={{
          background: color ?? "#374151",
          color: color ? "#fff" : "#e5e7eb",
          borderRadius: 4,
          padding: "1px 8px",
          fontSize: 12,
          fontWeight: 600,
        }}
      >
        {value}
      </span>
    </div>
  );
}

export function IncidentTicketPanel({ ticket, currentCheckpoint, completedCheckpoints }: Props) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16, height: "100%", overflow: "auto" }}>
      {/* Header */}
      <div>
        <div style={{ color: "#6b7280", fontSize: 10, letterSpacing: 1, textTransform: "uppercase", marginBottom: 4 }}>
          Incident Record
        </div>
        <div style={{ color: "#f59e0b", fontFamily: "monospace", fontSize: 13, fontWeight: 700 }}>
          {ticket.inc_number}
        </div>
        <div style={{ color: "#f3f4f6", fontWeight: 600, marginTop: 6, lineHeight: 1.4, fontSize: 14 }}>
          {ticket.title || <span style={{ color: "#6b7280", fontStyle: "italic" }}>No title yet</span>}
        </div>
      </div>

      {/* Priority row */}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        {ticket.priority && (
          <span
            style={{
              background: PRIORITY_COLOR[ticket.priority] ?? "#374151",
              color: "#fff",
              borderRadius: 4,
              padding: "2px 10px",
              fontSize: 13,
              fontWeight: 700,
            }}
          >
            {ticket.priority}
          </span>
        )}
        {ticket.status && (
          <span
            style={{
              background: ticket.status === "closed" ? "#166534" : "#1e3a5f",
              color: ticket.status === "closed" ? "#bbf7d0" : "#93c5fd",
              borderRadius: 4,
              padding: "2px 10px",
              fontSize: 12,
              fontWeight: 600,
            }}
          >
            {ticket.status.toUpperCase()}
          </span>
        )}
      </div>

      {/* Fields */}
      <div>
        <Badge label="Impact" value={ticket.impact ?? ""} />
        <Badge label="Urgency" value={ticket.urgency ?? ""} />
        {ticket.category && <Badge label="Category" value={ticket.category} />}
        {ticket.affected_users && <Badge label="Affected" value={ticket.affected_users} />}
        {ticket.assigned_to && <Badge label="Assigned to" value={ticket.assigned_to} />}
      </div>

      {/* Description */}
      {ticket.description && (
        <div>
          <div style={{ color: "#6b7280", fontSize: 11, letterSpacing: 1, textTransform: "uppercase", marginBottom: 6 }}>
            Description
          </div>
          <div style={{ color: "#d1d5db", fontSize: 13, lineHeight: 1.5 }}>{ticket.description}</div>
        </div>
      )}

      {/* Affected systems */}
      {ticket.affected_systems.length > 0 && (
        <div>
          <div style={{ color: "#6b7280", fontSize: 11, letterSpacing: 1, textTransform: "uppercase", marginBottom: 6 }}>
            Affected Systems
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
            {ticket.affected_systems.map((s) => (
              <span
                key={s}
                style={{
                  background: "#1f2937",
                  border: "1px solid #374151",
                  color: "#9ca3af",
                  borderRadius: 4,
                  padding: "1px 6px",
                  fontSize: 11,
                }}
              >
                {s}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Escalation contacts */}
      {ticket.escalation_contacts.length > 0 && (
        <div>
          <div style={{ color: "#6b7280", fontSize: 11, letterSpacing: 1, textTransform: "uppercase", marginBottom: 6 }}>
            Escalated To
          </div>
          {ticket.escalation_contacts.map((c) => (
            <div key={c} style={{ color: "#93c5fd", fontSize: 12 }}>
              {c}
            </div>
          ))}
        </div>
      )}

      {/* Workaround */}
      {ticket.workaround && (
        <div>
          <div style={{ color: "#6b7280", fontSize: 11, letterSpacing: 1, textTransform: "uppercase", marginBottom: 6 }}>
            Workaround
          </div>
          <div style={{ color: "#86efac", fontSize: 12, lineHeight: 1.5 }}>{ticket.workaround}</div>
        </div>
      )}

      {/* Checkpoint progress */}
      <div style={{ marginTop: "auto", paddingTop: 12, borderTop: "1px solid #374151" }}>
        <div style={{ color: "#6b7280", fontSize: 11, letterSpacing: 1, textTransform: "uppercase", marginBottom: 8 }}>
          ITIL Checkpoints
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          {CHECKPOINTS.map((cp) => {
            const done = completedCheckpoints.includes(cp);
            const active = currentCheckpoint === cp;
            return (
              <div
                key={cp}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  opacity: done || active ? 1 : 0.4,
                }}
              >
                <span
                  style={{
                    width: 8,
                    height: 8,
                    borderRadius: "50%",
                    background: done ? "#22c55e" : active ? "#f59e0b" : "#374151",
                    border: active ? "2px solid #fbbf24" : "none",
                    flexShrink: 0,
                  }}
                />
                <span
                  style={{
                    color: done ? "#4ade80" : active ? "#fbbf24" : "#6b7280",
                    fontSize: 12,
                    fontWeight: active ? 700 : 400,
                    textTransform: "capitalize",
                  }}
                >
                  {cp}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
