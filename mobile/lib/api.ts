// EXPO_PUBLIC_-prefixed vars are inlined at build time by Expo. A phone
// running Expo Go is a separate device on the network, so "localhost" won't
// reach your laptop — set this to your laptop's LAN IP, e.g.
// EXPO_PUBLIC_API_URL=http://192.168.1.42:8001 in mobile/.env (untracked).
const API_BASE = process.env.EXPO_PUBLIC_API_URL || "http://localhost:8001";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options?.headers || {}) },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      // ignore
    }
    throw new Error(detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) => request<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  put: <T>(path: string, body?: unknown) => request<T>(path, { method: "PUT", body: body ? JSON.stringify(body) : undefined }),
  del: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};

export interface Course {
  id: string;
  term: string;
  course_code: string;
  section: string;
  title: string | null;
  instructor: string | null;
  days: string | null;
  start_time: string | null;
  end_time: string | null;
  location: string | null;
}

export interface Task {
  id: string;
  title: string;
  notes: string | null;
  due_at: string | null;
  priority: string;
  status: string;
}

export interface Reminder {
  id: string;
  text: string;
  remind_at: string;
  status: string;
}

export interface Briefing {
  next_class: { course_code: string; title: string | null; start_time: string | null; end_time: string | null; location: string | null } | null;
  weather: { current_temp_c: number; current_condition: string; high_temp_c: number; low_temp_c: number } | null;
  assignments_due_today: { title: string; course: string | null; due_at: string | null }[];
  open_tasks: { id: string; title: string; due_at: string | null }[];
  pending_reminders: { id: string; text: string; remind_at: string }[];
}
