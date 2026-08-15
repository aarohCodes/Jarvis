"use client";

import { useEffect, useState } from "react";
import { api, Course } from "@/lib/api";

const emptyForm = {
  term: "26f",
  course_code: "",
  section: "",
  course_title: "",
  instructor: "",
  days: "",
  start_time: "",
  end_time: "",
  location: "",
};

export default function CoursesPage() {
  const [courses, setCourses] = useState<Course[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [lookupBusy, setLookupBusy] = useState(false);

  const load = () => api.get<Course[]>("/courses/schedule").then(setCourses).catch((e) => setError(e.message));

  useEffect(() => {
    load();
  }, []);

  const startEdit = (c: Course) => {
    setEditingId(c.id);
    setForm({
      term: c.term,
      course_code: c.course_code,
      section: c.section,
      course_title: c.title || "",
      instructor: c.instructor || "",
      days: c.days || "",
      start_time: c.start_time || "",
      end_time: c.end_time || "",
      location: c.location || "",
    });
  };

  const cancelEdit = () => {
    setEditingId(null);
    setForm(emptyForm);
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      if (editingId) {
        await api.put(`/courses/${editingId}`, {
          course_title: form.course_title || null,
          instructor: form.instructor || null,
          days: form.days || null,
          start_time: form.start_time || null,
          end_time: form.end_time || null,
          location: form.location || null,
        });
      } else {
        await api.post("/courses/manual", {
          ...form,
          course_title: form.course_title || null,
          instructor: form.instructor || null,
          days: form.days || null,
          start_time: form.start_time || null,
          end_time: form.end_time || null,
          location: form.location || null,
        });
      }
      cancelEdit();
      load();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const remove = async (id: string) => {
    setError(null);
    try {
      await api.del(`/courses/${id}`);
      load();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const tryCourseBookLookup = async (c: Course) => {
    setLookupBusy(true);
    setError(null);
    try {
      await api.post(`/courses/add?term=${c.term}&course_code=${c.course_code}&section=${c.section}`);
      load();
    } catch (e: any) {
      setError(`CourseBook lookup failed (expected until it's validated against a real browser session): ${e.message}`);
    } finally {
      setLookupBusy(false);
    }
  };

  return (
    <div>
      <h2 className="page-title">Courses</h2>
      {error && <div className="error-banner">{error}</div>}

      <div className="panel">
        <h3 className="panel-title">{editingId ? "Edit section" : "Add a section manually"}</h3>
        <form className="inline-form" onSubmit={submit}>
          <div className="field">
            <label>Term</label>
            <input value={form.term} disabled={!!editingId} onChange={(e) => setForm({ ...form, term: e.target.value })} placeholder="26f" required />
          </div>
          <div className="field">
            <label>Course code</label>
            <input value={form.course_code} disabled={!!editingId} onChange={(e) => setForm({ ...form, course_code: e.target.value })} placeholder="cs3345" required />
          </div>
          <div className="field">
            <label>Section</label>
            <input value={form.section} disabled={!!editingId} onChange={(e) => setForm({ ...form, section: e.target.value })} placeholder="004" required />
          </div>
          <div className="field">
            <label>Title</label>
            <input value={form.course_title} onChange={(e) => setForm({ ...form, course_title: e.target.value })} placeholder="Data Structures" />
          </div>
          <div className="field">
            <label>Instructor</label>
            <input value={form.instructor} onChange={(e) => setForm({ ...form, instructor: e.target.value })} />
          </div>
          <div className="field">
            <label>Days</label>
            <input value={form.days} onChange={(e) => setForm({ ...form, days: e.target.value })} placeholder="MW, TTh, etc" />
          </div>
          <div className="field">
            <label>Start</label>
            <input value={form.start_time} onChange={(e) => setForm({ ...form, start_time: e.target.value })} placeholder="10:00 am" />
          </div>
          <div className="field">
            <label>End</label>
            <input value={form.end_time} onChange={(e) => setForm({ ...form, end_time: e.target.value })} placeholder="11:15 am" />
          </div>
          <div className="field">
            <label>Location</label>
            <input value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} placeholder="ECSS 2.311" />
          </div>
          <button type="submit">{editingId ? "Save changes" : "Add section"}</button>
          {editingId && (
            <button type="button" className="secondary" onClick={cancelEdit}>
              Cancel
            </button>
          )}
        </form>
      </div>

      <div className="panel">
        <h3 className="panel-title">Schedule</h3>
        {courses.length === 0 ? (
          <p className="empty-state">No courses added yet.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Course</th>
                <th>Title</th>
                <th>Days</th>
                <th>Time</th>
                <th>Location</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {courses.map((c) => (
                <tr key={c.id}>
                  <td>
                    {c.course_code.toUpperCase()}.{c.section}
                  </td>
                  <td>{c.title || "—"}</td>
                  <td>{c.days || "—"}</td>
                  <td>
                    {c.start_time && c.end_time ? `${c.start_time} – ${c.end_time}` : "—"}
                  </td>
                  <td>{c.location || "—"}</td>
                  <td>
                    <button className="secondary" onClick={() => startEdit(c)}>
                      Edit
                    </button>{" "}
                    <button className="secondary" disabled={lookupBusy} onClick={() => tryCourseBookLookup(c)}>
                      Refresh from CourseBook
                    </button>{" "}
                    <button className="danger" onClick={() => remove(c.id)}>
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
