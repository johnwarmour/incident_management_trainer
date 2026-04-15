import { useState, useCallback } from "react";
import { api } from "./api";
import type {
  ChatMessage,
  CheckpointScore,
  Checkpoint,
  IncidentTicket,
  DebriefReport,
} from "./api";
import { IncidentTicketPanel } from "./components/IncidentTicket";
import { ChatPane } from "./components/ChatPane";
import { CheckpointPanel } from "./components/CheckpointPanel";
import { Debrief } from "./components/Debrief";

type AppPhase = "landing" | "loading" | "session" | "debrief";

const EMPTY_TICKET: IncidentTicket = {
  inc_number: "",
  title: "",
  description: "",
  category: "",
  affected_systems: [],
  impact: null,
  urgency: null,
  priority: null,
  affected_users: "",
  workaround: "",
  resolution: "",
  escalation_contacts: [],
  communication_sent: [],
  status: "open",
  assigned_to: "",
  notes: [],
};

export default function App() {
  const [phase, setPhase] = useState<AppPhase>("landing");
  const [sessionId, setSessionId] = useState("");
  const [scenarioTitle, setScenarioTitle] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [ticket, setTicket] = useState<IncidentTicket>(EMPTY_TICKET);
  const [checkpoint, setCheckpoint] = useState<Checkpoint>("detection");
  const [completedCheckpoints, setCompletedCheckpoints] = useState<Checkpoint[]>([]);
  const [lastScore, setLastScore] = useState<CheckpointScore | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [debrief, setDebrief] = useState<DebriefReport | null>(null);
  const [selectedScenario, setSelectedScenario] = useState<string | undefined>(undefined);

  const handleStart = useCallback(async () => {
    setPhase("loading");
    setError("");
    try {
      const res = await api.startSession(selectedScenario);
      setSessionId(res.session_id);
      setScenarioTitle(res.scenario_title);
      setMessages([{ role: "assistant", content: res.initial_message, checkpoint: "detection" }]);
      setTicket(res.ticket);
      setCheckpoint(res.current_checkpoint);
      setCompletedCheckpoints([]);
      setLastScore(null);
      setDebrief(null);
      setPhase("session");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to start session");
      setPhase("landing");
    }
  }, [selectedScenario]);

  const handleSend = useCallback(
    async (message: string) => {
      setLoading(true);
      setMessages((prev) => [...prev, { role: "user", content: message, checkpoint }]);
      try {
        const res = await api.sendInput(sessionId, message);
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: res.assistant_message, checkpoint: res.current_checkpoint },
        ]);
        setTicket(res.ticket);

        if (res.checkpoint_complete && res.checkpoint_score) {
          setCompletedCheckpoints((prev) => [...prev, checkpoint]);
          setLastScore(res.checkpoint_score);
          setCheckpoint(res.current_checkpoint);
        }

        if (res.session_complete) {
          const report = await api.getDebrief(sessionId);
          setDebrief(report);
          setPhase("debrief");
        }
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Error sending message");
      } finally {
        setLoading(false);
      }
    },
    [sessionId, checkpoint],
  );

  const handleForceAdvance = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.forceAdvance(sessionId);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: res.assistant_message, checkpoint: res.current_checkpoint },
      ]);
      setTicket(res.ticket);
      if (res.checkpoint_score) {
        setCompletedCheckpoints((prev) => [...prev, checkpoint]);
        setLastScore(res.checkpoint_score);
        setCheckpoint(res.current_checkpoint);
      }
      if (res.session_complete) {
        const report = await api.getDebrief(sessionId);
        setDebrief(report);
        setPhase("debrief");
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Error advancing checkpoint");
    } finally {
      setLoading(false);
    }
  }, [sessionId, checkpoint]);

  const handleRestart = useCallback(() => {
    setPhase("landing");
    setSessionId("");
    setMessages([]);
    setTicket(EMPTY_TICKET);
    setCheckpoint("detection");
    setCompletedCheckpoints([]);
    setLastScore(null);
    setDebrief(null);
    setError("");
  }, []);

  if (phase === "landing") {
    return (
      <LandingScreen
        onStart={handleStart}
        error={error}
        selected={selectedScenario}
        onSelect={setSelectedScenario}
      />
    );
  }

  if (phase === "loading") {
    return (
      <div style={fullScreenCenter}>
        <div style={{ textAlign: "center" }}>
          <div style={{ color: "#f59e0b", fontSize: 18, fontWeight: 600 }}>Generating scenario...</div>
          <div style={{ color: "#6b7280", marginTop: 8, fontSize: 13 }}>
            Claude is building a realistic incident for you
          </div>
        </div>
      </div>
    );
  }

  if (phase === "debrief" && debrief) {
    return (
      <div style={{ minHeight: "100vh", background: "#0f1117", color: "#f3f4f6", overflowY: "auto" }}>
        <Debrief report={debrief} onRestart={handleRestart} />
      </div>
    );
  }

  // Session view — three-panel layout
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "260px 1fr 260px",
        gridTemplateRows: "48px 1fr",
        height: "100vh",
        background: "#0f1117",
        color: "#f3f4f6",
        overflow: "hidden",
      }}
    >
      {/* Top bar */}
      <div
        style={{
          gridColumn: "1 / -1",
          display: "flex",
          alignItems: "center",
          gap: 16,
          padding: "0 16px",
          borderBottom: "1px solid #1f2937",
          background: "#111827",
        }}
      >
        <span style={{ color: "#f59e0b", fontWeight: 700, fontSize: 14 }}>INCIDENT SIM</span>
        <span style={{ color: "#6b7280", fontSize: 12 }}>|</span>
        <span
          style={{
            color: "#d1d5db",
            fontSize: 13,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {scenarioTitle}
        </span>
        {error && (
          <span style={{ color: "#f87171", fontSize: 12, marginLeft: "auto" }}>{error}</span>
        )}
      </div>

      {/* Left: Incident Ticket */}
      <div style={{ borderRight: "1px solid #1f2937", padding: 16, overflow: "auto" }}>
        <IncidentTicketPanel
          ticket={ticket}
          currentCheckpoint={checkpoint}
          completedCheckpoints={completedCheckpoints}
        />
      </div>

      {/* Center: Chat */}
      <ChatPane
        messages={messages}
        onSend={handleSend}
        loading={loading}
        disabled={phase !== "session"}
      />

      {/* Right: Checkpoint panel */}
      <div style={{ borderLeft: "1px solid #1f2937", padding: 16, overflow: "auto" }}>
        <CheckpointPanel
          checkpoint={checkpoint}
          ticket={ticket}
          completedCheckpoints={completedCheckpoints}
          lastScore={lastScore}
          onForceAdvance={handleForceAdvance}
          loading={loading}
          sessionComplete={phase !== "session"}
        />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Landing screen
// ---------------------------------------------------------------------------

const SCENARIO_OPTIONS: { value: string | undefined; label: string; description: string }[] = [
  { value: undefined, label: "Random", description: "Surprise me" },
  { value: "database_outage", label: "Database Outage", description: "Primary DB becomes unresponsive" },
  { value: "ddos_attack", label: "DDoS Attack", description: "Volumetric attack on web tier" },
  { value: "cert_expiry", label: "Certificate Expiry", description: "TLS cert causes HTTPS failures" },
  { value: "deployment_regression", label: "Deployment Regression", description: "Code deploy breaks payments" },
  { value: "third_party_api_failure", label: "Third-Party Failure", description: "Critical vendor goes down" },
];

function LandingScreen({
  onStart,
  error,
  selected,
  onSelect,
}: {
  onStart: () => void;
  error: string;
  selected: string | undefined;
  onSelect: (v: string | undefined) => void;
}) {
  return (
    <div style={{ ...fullScreenCenter, flexDirection: "column", gap: 32, padding: 24 }}>
      <div style={{ textAlign: "center" }}>
        <div style={{ fontSize: 36, fontWeight: 800, color: "#f59e0b", letterSpacing: -1 }}>
          INCIDENT SIM
        </div>
        <div style={{ color: "#6b7280", fontSize: 15, marginTop: 8, maxWidth: 440, lineHeight: 1.5 }}>
          AI-powered ITIL incident management training. Practice all six checkpoints with realistic scenarios.
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 8, width: "100%", maxWidth: 400 }}>
        <div style={{ color: "#9ca3af", fontSize: 12, letterSpacing: 1, textTransform: "uppercase" }}>
          Choose a scenario
        </div>
        {SCENARIO_OPTIONS.map((opt) => (
          <button
            key={opt.label}
            onClick={() => onSelect(opt.value)}
            style={{
              background: selected === opt.value ? "#1e3a5f" : "#111827",
              border: `1px solid ${selected === opt.value ? "#2563eb" : "#374151"}`,
              borderRadius: 8,
              padding: "10px 16px",
              cursor: "pointer",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              color: "#f3f4f6",
              textAlign: "left",
            }}
          >
            <span style={{ fontWeight: 600, fontSize: 14 }}>{opt.label}</span>
            <span style={{ color: "#6b7280", fontSize: 12 }}>{opt.description}</span>
          </button>
        ))}
      </div>

      {error && (
        <div
          style={{
            color: "#f87171",
            fontSize: 13,
            background: "#1f1010",
            padding: "8px 16px",
            borderRadius: 6,
          }}
        >
          {error}
        </div>
      )}

      <button
        onClick={onStart}
        style={{
          background: "#2563eb",
          color: "#fff",
          border: "none",
          borderRadius: 10,
          padding: "14px 48px",
          fontSize: 16,
          fontWeight: 700,
          cursor: "pointer",
          letterSpacing: 0.5,
        }}
      >
        Start Simulation
      </button>
    </div>
  );
}

const fullScreenCenter: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  minHeight: "100vh",
  background: "#0f1117",
  color: "#f3f4f6",
};
