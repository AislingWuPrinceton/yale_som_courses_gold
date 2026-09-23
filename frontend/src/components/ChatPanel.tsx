import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { sendChat } from "../api";
import { SproutIcon } from "./icons";

interface Message {
  role: "user" | "assistant";
  text: string;
  tools?: string[];
  error?: boolean;
}

const SUGGESTIONS = [
  "Which courses meet on Wednesday?",
  "What is MGT 887 Negotiations about?",
  "Find electives on sustainability",
];

/** Render the agent's light markdown (**bold**, "- " bullets) as safe nodes. */
function rich(text: string): ReactNode {
  return text.split("\n").map((line, i) => {
    const bullet = /^\s*[-*]\s+/.test(line);
    const body = bullet ? line.replace(/^\s*[-*]\s+/, "") : line;
    const parts = body.split(/(\*\*[^*]+\*\*)/g).filter(Boolean);
    const nodes = parts.map((p, j) =>
      p.startsWith("**") && p.endsWith("**") ? (
        <strong key={j}>{p.slice(2, -2)}</strong>
      ) : (
        <span key={j}>{p.replace(/^#+\s*/, "")}</span>
      ),
    );
    return (
      <div key={i} style={bullet ? { paddingLeft: "0.9rem", textIndent: "-0.9rem" } : undefined}>
        {bullet ? "• " : ""}
        {nodes}
      </div>
    );
  });
}

export default function ChatPanel() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    logRef.current?.scrollTo({
      top: logRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, busy]);

  async function ask(question: string) {
    const text = question.trim();
    if (!text || busy) return;

    setMessages((m) => [...m, { role: "user", text }]);
    setInput("");
    setBusy(true);

    try {
      const res = await sendChat(text);
      setMessages((m) => [
        ...m,
        { role: "assistant", text: res.reply, tools: res.tools_used },
      ]);
    } catch (err) {
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          error: true,
          text:
            "Could not reach the course agent. Is the backend running on port 8000? " +
            `(${err instanceof Error ? err.message : "unknown error"})`,
        },
      ]);
    } finally {
      setBusy(false);
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    void ask(input);
  }

  return (
    <aside className="chat">
      <div className="chat-head">
        <SproutIcon />
        <h2>Course Assistant</h2>
        <span className="sub">gpt-6-astra</span>
      </div>

      <div className="chat-log" ref={logRef}>
        {messages.length === 0 && !busy && (
          <div className="empty">
            <SproutIcon />
            <p>
              Ask about courses, faculty, or schedules. I search the catalog
              first, and the web when it isn't enough.
            </p>
            <div className="suggestions">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  type="button"
                  className="suggestion"
                  onClick={() => void ask(s)}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <div
            key={i}
            className={`msg ${m.role}${m.error ? " error" : ""}`}
          >
            <div className="bubble">{rich(m.text)}</div>
            {m.tools && m.tools.length > 0 && (
              <div className="tools">
                <span>used</span>
                {m.tools.map((t) => (
                  <code key={t} className="tool-chip">
                    {t}
                  </code>
                ))}
              </div>
            )}
          </div>
        ))}

        {busy && (
          <div className="msg assistant">
            <div className="bubble">
              <span className="thinking">
                Thinking
                <span className="dots">
                  <span>.</span>
                  <span>.</span>
                  <span>.</span>
                </span>
              </span>
            </div>
          </div>
        )}
      </div>

      <form className="chat-form" onSubmit={onSubmit}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about a course, professor, or time…"
          aria-label="Ask the course assistant"
          disabled={busy}
        />
        <button className="send" type="submit" disabled={busy || !input.trim()}>
          Send
        </button>
      </form>
    </aside>
  );
}
