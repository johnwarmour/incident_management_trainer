import type { DebriefReport, Checkpoint } from "../api";

interface Props {
  report: DebriefReport;
  onRestart: () => void;
}

const CHECKPOINT_LABELS: Record<Checkpoint, string> = {
  detection: "Detection",
  triage: "Triage",
  escalation: "Escalation",
  communication: "Communication",
  resolution: "Resolution",
  closure: "Closure",
};

function ScoreBar({ score, max }: { score: number; max: number }) {
  const pct = (score / max) * 100;
  const color = score >= 80 ? "#22c55e" : score >= 60 ? "#f59e0b" : "#ef4444";
  return (
    <div style={{ background: "#1f2937", borderRadius: 4, height: 6, width: "100%" }}>
      <div
        style={{
          width: `${pct}%`,
          height: "100%",
          background: color,
          borderRadius: 4,
          transition: "width 0.6s ease",
        }}
      />
    </div>
  );
}

export function Debrief({ report, onRestart }: Props) {
  const overallColor =
    report.overall_score >= 80 ? "#22c55e" : report.overall_score >= 60 ? "#f59e0b" : "#ef4444";

  return (
    <div
      style={{
        maxWidth: 700,
        margin: "0 auto",
        padding: 24,
        display: "flex",
        flexDirection: "column",
        gap: 24,
      }}
    >
      {/* Header */}
      <div style={{ textAlign: "center" }}>
        <div style={{ color: "#6b7280", fontSize: 12, letterSpacing: 2, textTransform: "uppercase" }}>
          Simulation Complete
        </div>
        <div style={{ color: "#f3f4f6", fontSize: 22, fontWeight: 700, margin: "8px 0" }}>
          {report.scenario_title}
        </div>
        <div
          style={{
            fontSize: 56,
            fontWeight: 800,
            color: overallColor,
            lineHeight: 1,
          }}
        >
          {report.overall_score}
          <span style={{ fontSize: 20, color: "#6b7280" }}>/{report.total_possible / report.scores.length}</span>
        </div>
        <div style={{ color: "#6b7280", fontSize: 13 }}>Overall average score</div>
      </div>

      {/* Per-checkpoint scores */}
      <div
        style={{
          background: "#111827",
          border: "1px solid #1f2937",
          borderRadius: 10,
          padding: 20,
          display: "flex",
          flexDirection: "column",
          gap: 16,
        }}
      >
        <div style={{ color: "#6b7280", fontSize: 11, letterSpacing: 1, textTransform: "uppercase" }}>
          Checkpoint Breakdown
        </div>
        {report.scores.map((s) => (
          <div key={s.checkpoint}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: 4,
              }}
            >
              <span style={{ color: "#d1d5db", fontSize: 14, fontWeight: 600, textTransform: "capitalize" }}>
                {CHECKPOINT_LABELS[s.checkpoint]}
              </span>
              <span
                style={{
                  fontSize: 14,
                  fontWeight: 700,
                  color: s.score >= 80 ? "#22c55e" : s.score >= 60 ? "#f59e0b" : "#ef4444",
                }}
              >
                {s.score}/{s.max_score}
              </span>
            </div>
            <ScoreBar score={s.score} max={s.max_score} />
            <div style={{ color: "#9ca3af", fontSize: 12, marginTop: 4, lineHeight: 1.4 }}>
              {s.feedback}
            </div>
            {s.good_decisions.length > 0 && (
              <div style={{ marginTop: 6 }}>
                {s.good_decisions.map((g) => (
                  <div key={g} style={{ color: "#4ade80", fontSize: 11, display: "flex", gap: 4 }}>
                    <span>✓</span>
                    <span>{g}</span>
                  </div>
                ))}
              </div>
            )}
            {s.missed_items.length > 0 && (
              <div style={{ marginTop: 2 }}>
                {s.missed_items.map((m) => (
                  <div key={m} style={{ color: "#f87171", fontSize: 11, display: "flex", gap: 4 }}>
                    <span>✗</span>
                    <span>{m}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Overall feedback */}
      <div
        style={{
          background: "#111827",
          border: "1px solid #1f2937",
          borderRadius: 10,
          padding: 20,
        }}
      >
        <div style={{ color: "#6b7280", fontSize: 11, letterSpacing: 1, textTransform: "uppercase", marginBottom: 10 }}>
          Instructor Feedback
        </div>
        <div style={{ color: "#d1d5db", fontSize: 14, lineHeight: 1.7, whiteSpace: "pre-wrap" }}>
          {report.overall_feedback}
        </div>
      </div>

      {/* Restart */}
      <div style={{ textAlign: "center" }}>
        <button
          onClick={onRestart}
          style={{
            background: "#2563eb",
            color: "#fff",
            border: "none",
            borderRadius: 8,
            padding: "12px 32px",
            fontSize: 15,
            fontWeight: 700,
            cursor: "pointer",
          }}
        >
          Start New Simulation
        </button>
      </div>
    </div>
  );
}
