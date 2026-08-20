"use client";

import { useEffect, useRef, useState } from "react";
import { api, Briefing } from "@/lib/api";
import { useClock } from "@/lib/useClock";

type ChatEntry = { role: "user" | "assistant"; content: string };
type CoreState = "idle" | "thinking";

const SESSION_ID = "default";

const STATUS_LABEL: Record<CoreState, string> = {
  idle: "STANDING BY",
  thinking: "PROCESSING…",
};

export default function CommandDeckPage() {
  const now = useClock();

  // -- chat state --
  const [messages, setMessages] = useState<ChatEntry[]>([]);
  const [input, setInput] = useState("");
  const [coreState, setCoreState] = useState<CoreState>("idle");
  const [chatError, setChatError] = useState<string | null>(null);

  // -- briefing state --
  const [briefing, setBriefing] = useState<Briefing | null>(null);
  const [briefingError, setBriefingError] = useState<string | null>(null);

  const transcriptRef = useRef<HTMLDivElement>(null);

  // shared "no data yet" fallback for briefing panels — surfaces the fetch
  // error instead of spinning on "establishing uplink" forever when it fails
  const briefingPending = (
    <p className="empty-state">{briefingError ? `// uplink error — ${briefingError}` : "// establishing uplink…"}</p>
  );

  useEffect(() => {
    api
      .get<{ role: "user" | "assistant"; content: string }[]>(`/chat/history?session_id=${SESSION_ID}`)
      .then((rows) => setMessages(rows.map((r) => ({ role: r.role, content: r.content }))))
      .catch(() => {
        /* fresh session is fine */
      });

    api
      .get<Briefing>("/briefing/morning")
      .then(setBriefing)
      .catch((e) => setBriefingError(e.message));
  }, []);

  useEffect(() => {
    transcriptRef.current?.scrollTo({ top: transcriptRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, coreState]);

  const sendMessage = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed) return;
    setChatError(null);
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: trimmed }]);
    setCoreState("thinking");
    try {
      const res = await api.post<{ reply: string }>("/chat", { message: trimmed, session_id: SESSION_ID });
      setMessages((prev) => [...prev, { role: "assistant", content: res.reply }]);
      setCoreState("idle");
    } catch (e: any) {
      setChatError(e.message);
      setCoreState("idle");
    }
  };

  return (
    <div className="command-deck">
      <header className="deck-header">
        <div>
          <h1 className="deck-title">Command Deck</h1>
          <p className="deck-subtitle">// text interface online — voice pending ElevenLabs integration.</p>
        </div>
        <div className="deck-meta">
          <span className="deck-date">
            {now ? now.toLocaleDateString([], { weekday: "short", month: "short", day: "numeric" }) : "—"}
          </span>
          <span className="deck-time">{now ? now.toLocaleTimeString([], { hour12: false }) : "--:--:--"}</span>
        </div>
      </header>

      <div className="deck-grid">
        {/* -------- left: instrument cluster -------- */}
        <div className="deck-col deck-col-left">
          <div className="panel instrument">
            <h3 className="panel-title">Next Class</h3>
            {!briefing ? (
              briefingPending
            ) : briefing.next_class ? (
              <>
                <div className="instrument-value">
                  {(briefing.next_class.title || briefing.next_class.course_code).toString().toUpperCase()}
                </div>
                <div className="instrument-sub">
                  {briefing.next_class.start_time} – {briefing.next_class.end_time}
                </div>
                <div className="instrument-sub">{briefing.next_class.location}</div>
              </>
            ) : (
              <p className="empty-state">No more classes today.</p>
            )}
          </div>

          <div className="panel instrument">
            <h3 className="panel-title">Atmospheric</h3>
            {briefing?.weather ? (
              <>
                <div className="instrument-value">{briefing.weather.current_temp_c}°C</div>
                <div className="instrument-sub">{briefing.weather.current_condition}</div>
                <div className="instrument-sub">
                  High {briefing.weather.high_temp_c}° / Low {briefing.weather.low_temp_c}°
                </div>
              </>
            ) : briefing ? (
              <p className="empty-state">
                Set a home location on <a href="/preferences">Preferences</a> to enable weather.
              </p>
            ) : (
              briefingPending
            )}
          </div>
        </div>

        {/* -------- center: core + transcript -------- */}
        <div className="deck-col deck-col-center">
          <div className="chat-core-wrap">
            <div className={`chat-core size-hero state-${coreState}`}>
              <div className="chat-core-ring r1" />
              <div className="chat-core-ring r2" />
              <div className="chat-core-ring r3" />
              <div className="chat-core-dot" />
            </div>
            <div className="chat-status">{STATUS_LABEL[coreState]}</div>
          </div>

          {chatError && <div className="error-banner">{chatError}</div>}

          <div className="panel chat-transcript" ref={transcriptRef}>
            {messages.length === 0 ? (
              <p className="empty-state">// no transmission history — say something, sir.</p>
            ) : (
              messages.map((m, i) => (
                <div key={i} className={`chat-line ${m.role}`}>
                  <span className="chat-line-tag">{m.role === "user" ? "YOU" : "JARVIS"}</span>
                  <span className="chat-line-text">{m.content}</span>
                </div>
              ))
            )}
          </div>

          <form
            className="chat-input-row"
            onSubmit={(e) => {
              e.preventDefault();
              sendMessage(input);
            }}
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type a command…"
              autoComplete="off"
            />
            <button type="submit">Send</button>
          </form>
        </div>

        {/* -------- right: manifest dock -------- */}
        <div className="deck-col deck-col-right">
          <div className="panel manifest">
            <h3 className="panel-title">Due Today</h3>
            {!briefing ? (
              briefingPending
            ) : briefing.assignments_due_today.length === 0 ? (
              <p className="empty-state">Nothing due today.</p>
            ) : (
              <ul className="manifest-list">
                {briefing.assignments_due_today.map((a, i) => (
                  <li key={i}>
                    {a.title} {a.course ? `(${a.course})` : ""}
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="panel manifest">
            <h3 className="panel-title">Open Tasks</h3>
            {!briefing ? (
              briefingPending
            ) : briefing.open_tasks.length === 0 ? (
              <p className="empty-state">No open tasks.</p>
            ) : (
              <ul className="manifest-list">
                {briefing.open_tasks.map((t) => (
                  <li key={t.id}>{t.title}</li>
                ))}
              </ul>
            )}
          </div>

          <div className="panel manifest">
            <h3 className="panel-title">Pending Reminders</h3>
            {!briefing ? (
              briefingPending
            ) : briefing.pending_reminders.length === 0 ? (
              <p className="empty-state">No pending reminders.</p>
            ) : (
              <ul className="manifest-list">
                {briefing.pending_reminders.map((r) => (
                  <li key={r.id}>
                    {r.text} — {new Date(r.remind_at).toLocaleString()}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
