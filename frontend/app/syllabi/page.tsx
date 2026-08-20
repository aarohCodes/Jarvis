"use client";

import { useEffect, useRef, useState } from "react";
import { Syllabus } from "@/lib/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

export default function SyllabiPage() {
  const [syllabi, setSyllabi] = useState<Syllabus[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [courseCode, setCourseCode] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const [askCourse, setAskCourse] = useState("");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<string | null>(null);

  const load = async () => {
    try {
      const res = await fetch(`${API_BASE}/syllabus`, { cache: "no-store" });
      if (!res.ok) throw new Error(res.statusText);
      setSyllabi(await res.json());
    } catch (e: any) {
      setError(e.message);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const upload = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    const file = fileRef.current?.files?.[0];
    if (!file || !courseCode) return;
    const form = new FormData();
    form.append("course_code", courseCode);
    form.append("file", file);
    try {
      const res = await fetch(`${API_BASE}/syllabus/upload`, { method: "POST", body: form });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || res.statusText);
      }
      setCourseCode("");
      if (fileRef.current) fileRef.current.value = "";
      load();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const remove = async (code: string) => {
    try {
      const res = await fetch(`${API_BASE}/syllabus/${code}`, { method: "DELETE" });
      if (!res.ok) throw new Error(res.statusText);
      load();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const ask = async (e: React.FormEvent) => {
    e.preventDefault();
    setAnswer(null);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/syllabus/ask?course_code=${encodeURIComponent(askCourse)}&question=${encodeURIComponent(question)}`);
      const body = await res.json();
      if (!res.ok) throw new Error(body.detail || res.statusText);
      setAnswer(body.answer);
    } catch (e: any) {
      setError(e.message);
    }
  };

  return (
    <div>
      <h2 className="page-title">Syllabi</h2>
      {error && <div className="error-banner">{error}</div>}

      <div className="panel">
        <h3 className="panel-title">Upload a syllabus</h3>
        <form className="inline-form" onSubmit={upload}>
          <div className="field">
            <label>Course code</label>
            <input value={courseCode} onChange={(e) => setCourseCode(e.target.value)} placeholder="cs3345" required />
          </div>
          <div className="field">
            <label>PDF or photo</label>
            <input type="file" accept="application/pdf,image/*" ref={fileRef} required />
          </div>
          <button type="submit">Upload</button>
        </form>
        <p className="empty-state" style={{ marginTop: 8 }}>
          A PDF is extracted directly; a photo/screenshot is read by Gemini vision instead.
        </p>
      </div>

      <div className="panel">
        <h3 className="panel-title">Ask a question</h3>
        <form className="inline-form" onSubmit={ask}>
          <div className="field">
            <label>Course code</label>
            <input value={askCourse} onChange={(e) => setAskCourse(e.target.value)} placeholder="cs3345" required />
          </div>
          <div className="field">
            <label>Question</label>
            <input value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="When are office hours?" required />
          </div>
          <button type="submit">Ask</button>
        </form>
        {answer && (
          <p style={{ whiteSpace: "pre-wrap", fontSize: 14 }}>
            <strong>Answer:</strong> {answer}
          </p>
        )}
        <p className="empty-state">Naive keyword-match placeholder until the LLM chat layer answers this using full context.</p>
      </div>

      <div className="panel">
        <h3 className="panel-title">Uploaded syllabi</h3>
        {syllabi.length === 0 ? (
          <p className="empty-state">Nothing uploaded yet.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Course</th>
                <th>File</th>
                <th>Uploaded</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {syllabi.map((s) => (
                <tr key={s.course_code}>
                  <td>{s.course_code.toUpperCase()}</td>
                  <td>{s.file_name}</td>
                  <td>{new Date(s.uploaded_at).toLocaleString()}</td>
                  <td>
                    <button className="danger" onClick={() => remove(s.course_code)}>
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
