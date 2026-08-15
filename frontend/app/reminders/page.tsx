"use client";

import { useEffect, useState } from "react";
import { api, Reminder } from "@/lib/api";

export default function RemindersPage() {
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [text, setText] = useState("");
  const [remindAt, setRemindAt] = useState("");

  const load = () => api.get<Reminder[]>("/reminders").then(setReminders).catch((e) => setError(e.message));

  useEffect(() => {
    load();
  }, []);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await api.post("/reminders", { text, remind_at: new Date(remindAt).toISOString() });
      setText("");
      setRemindAt("");
      load();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const remove = async (id: string) => {
    await api.del(`/reminders/${id}`);
    load();
  };

  return (
    <div>
      <h2 className="page-title">Reminders</h2>
      {error && <div className="error-banner">{error}</div>}

      <div className="panel">
        <h3 className="panel-title">New reminder</h3>
        <form className="inline-form" onSubmit={submit}>
          <div className="field">
            <label>Text</label>
            <input value={text} onChange={(e) => setText(e.target.value)} required placeholder="Remind me about the sleepover" />
          </div>
          <div className="field">
            <label>When</label>
            <input type="datetime-local" value={remindAt} onChange={(e) => setRemindAt(e.target.value)} required />
          </div>
          <button type="submit">Add reminder</button>
        </form>
        <p className="empty-state">
          Fires via the backend&apos;s 60-second poll job; delivery is logged to the console/action_log for now until push notifications exist.
        </p>
      </div>

      <div className="panel">
        <h3 className="panel-title">All reminders</h3>
        {reminders.length === 0 ? (
          <p className="empty-state">No reminders yet.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Text</th>
                <th>Remind at</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {reminders.map((r) => (
                <tr key={r.id}>
                  <td>{r.text}</td>
                  <td>{new Date(r.remind_at).toLocaleString()}</td>
                  <td>
                    <span className={`badge status-${r.status}`}>{r.status}</span>
                  </td>
                  <td>
                    <button className="danger" onClick={() => remove(r.id)}>
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
