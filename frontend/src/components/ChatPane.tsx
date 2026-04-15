import { useEffect, useRef, useState } from "react";
import type { ChatMessage } from "../api";

interface Props {
  messages: ChatMessage[];
  onSend: (message: string) => void;
  loading: boolean;
  disabled: boolean;
}

export function ChatPane({ messages, onSend, loading, disabled }: Props) {
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const msg = input.trim();
    if (!msg || loading || disabled) return;
    setInput("");
    onSend(msg);
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as unknown as React.FormEvent);
    }
  }

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        overflow: "hidden",
      }}
    >
      {/* Messages */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "12px 8px",
          display: "flex",
          flexDirection: "column",
          gap: 12,
        }}
      >
        {messages.map((msg, i) => (
          <MessageBubble key={i} msg={msg} />
        ))}
        {loading && (
          <div style={{ display: "flex", gap: 6, alignItems: "center", padding: "4px 0" }}>
            <TypingIndicator />
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <form
        onSubmit={handleSubmit}
        style={{
          padding: "8px",
          borderTop: "1px solid #374151",
          display: "flex",
          gap: 8,
          alignItems: "flex-end",
        }}
      >
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled || loading}
          placeholder={
            disabled
              ? "Session complete — view debrief above"
              : "Type your response... (Enter to send, Shift+Enter for newline)"
          }
          rows={2}
          style={{
            flex: 1,
            background: "#1f2937",
            border: "1px solid #374151",
            borderRadius: 6,
            color: "#f3f4f6",
            padding: "8px 12px",
            fontSize: 14,
            resize: "none",
            fontFamily: "inherit",
            outline: "none",
          }}
        />
        <button
          type="submit"
          disabled={disabled || loading || !input.trim()}
          style={{
            background: loading || disabled ? "#374151" : "#2563eb",
            color: "#fff",
            border: "none",
            borderRadius: 6,
            padding: "8px 16px",
            cursor: disabled || loading ? "not-allowed" : "pointer",
            fontSize: 14,
            fontWeight: 600,
            height: 52,
          }}
        >
          Send
        </button>
      </form>
    </div>
  );
}

function MessageBubble({ msg }: { msg: ChatMessage }) {
  const isUser = msg.role === "user";
  return (
    <div
      style={{
        display: "flex",
        justifyContent: isUser ? "flex-end" : "flex-start",
      }}
    >
      <div
        style={{
          maxWidth: "88%",
          background: isUser ? "#1d4ed8" : "#1f2937",
          border: isUser ? "none" : "1px solid #374151",
          borderRadius: isUser ? "12px 12px 2px 12px" : "12px 12px 12px 2px",
          padding: "8px 12px",
          color: "#f3f4f6",
          fontSize: 14,
          lineHeight: 1.6,
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
        }}
      >
        {msg.content}
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div
      style={{
        background: "#1f2937",
        border: "1px solid #374151",
        borderRadius: "12px 12px 12px 2px",
        padding: "8px 16px",
        display: "flex",
        gap: 4,
        alignItems: "center",
      }}
    >
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          style={{
            width: 6,
            height: 6,
            borderRadius: "50%",
            background: "#6b7280",
            animation: `bounce 1.2s ease-in-out ${i * 0.2}s infinite`,
          }}
        />
      ))}
      <style>{`
        @keyframes bounce {
          0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
          40% { transform: translateY(-4px); opacity: 1; }
        }
      `}</style>
    </div>
  );
}
