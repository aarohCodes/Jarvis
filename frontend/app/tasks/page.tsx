"use client";

import { useEffect, useState } from "react";
import { api, Task } from "@/lib/api";

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [notes, setNotes] = useState("");
  const [dueAt, setDueAt] = useState("");
  const [priority, setPriority] = useState("normal");
  const [showCompleted, setShowCompleted] = useState(false);

  const load = () =>
    api
      .get<Task[]>(showCompleted ? "/tasks" : "/tasks?status=open")
      .then(setTasks)
      .catch((e) => setError(e.message));

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showCompleted]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await api.post("/tasks", {
        title,
        notes: notes || null,
        due_at: dueAt ? new Date(dueAt).toISOString() : null,
        priority,
      });
      setTitle("");
      setNotes("");
      setDueAt("");
      setPriority("normal");
      load();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const complete = async (id: string) => {
    await api.put(`/tasks/${id}`, { status: "completed" });
    load();
  };

  const remove = async (id: string) => {
    await api.del(`/tasks/${id}`);
    load();
  };

  return (
    <div>
      <h2 className="page-title">Tasks</h2>
      {error && <div className="error-banner">{error}</div>}

      <div className="panel">
        <h3 className="panel-title">Add a task</h3>
        <form className="inline-form" onSubmit={submit}>
          <div className="field">
            <label>Title</label>
            <input value={title} onChange={(e) => setTitle(e.target.value)} required />
          </div>
          <div className="field">
            <label>Notes</label>
            <input value={notes} onChange={(e) => setNotes(e.target.value)} />
          </div>
          <div className="field">
            <label>Due</label>
            <input type="datetime-local" value={dueAt} onChange={(e) => setDueAt(e.target.value)} />
          </div>
          <div className="field">
            <label>Priority</label>
            <select value={priority} onChange={(e) => setPriority(e.target.value)}>
              <option value="low">Low</option>
              <option value="normal">Normal</option>
              <option value="high">High</option>
            </select>
          </div>
          <button type="submit">Add task</button>
        </form>
      </div>

      <div className="panel">
        <h3 className="panel-title">
          Tasks{" "}
          <label
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: 10,
              fontWeight: 400,
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              color: "var(--text-dim)",
              marginLeft: 10,
            }}
          >
            <input type="checkbox" checked={showCompleted} onChange={(e) => setShowCompleted(e.target.checked)} /> show completed
          </label>
        </h3>
        {tasks.length === 0 ? (
          <p className="empty-state">Nothing here.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Title</th>
                <th>Due</th>
                <th>Priority</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {tasks.map((t) => (
                <tr key={t.id}>
                  <td>
                    {t.title}
                    {t.notes && <div style={{ color: "var(--text-dim)", fontSize: 12 }}>{t.notes}</div>}
                  </td>
                  <td>{t.due_at ? new Date(t.due_at).toLocaleString() : "—"}</td>
                  <td>{t.priority}</td>
                  <td>
                    <span className={`badge status-${t.status}`}>{t.status}</span>
                  </td>
                  <td>
                    {t.status !== "completed" && (
                      <button className="secondary" onClick={() => complete(t.id)}>
                        Complete
                      </button>
                    )}{" "}
                    <button className="danger" onClick={() => remove(t.id)}>
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
