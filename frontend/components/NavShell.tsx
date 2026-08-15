"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { useClock } from "@/lib/useClock";

const NAV_ITEMS = [
  { href: "/", label: "Jarvis", glyph: "00" },
  { href: "/courses", label: "Courses", glyph: "01" },
  { href: "/tasks", label: "Tasks", glyph: "02" },
  { href: "/reminders", label: "Reminders", glyph: "03" },
  { href: "/syllabi", label: "Syllabi", glyph: "04" },
  { href: "/preferences", label: "Preferences", glyph: "05" },
];

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

function useBackendStatus() {
  const [online, setOnline] = useState<boolean | null>(null);
  useEffect(() => {
    let cancelled = false;
    const ping = () => {
      fetch(`${API_BASE}/health`, { cache: "no-store" })
        .then((r) => r.json())
        .then((body) => !cancelled && setOnline(Boolean(body.database)))
        .catch(() => !cancelled && setOnline(false));
    };
    ping();
    const id = setInterval(ping, 15000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);
  return online;
}

export default function NavShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const now = useClock();
  const online = useBackendStatus();
  const isHero = pathname === "/";

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="core">
          <div className="core-ring core-ring-outer" />
          <div className="core-ring core-ring-mid" />
          <div className="core-ring core-ring-inner" />
          <div className="core-dot" />
        </div>
        <div className="wordmark">
          <span>JARVIS</span>
        </div>

        <nav>
          {NAV_ITEMS.map((item) => {
            const active = pathname === item.href;
            return (
              <Link key={item.href} href={item.href} className={`nav-item ${active ? "active" : ""}`} title={item.label}>
                <span className="nav-glyph">{item.glyph}</span>
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="sidebar-footer">
          <div className="status-row">
            <span className={`status-dot ${online === null ? "pending" : online ? "online" : "offline"}`} />
            <span>{online === null ? "SYNC" : online ? "ONLINE" : "LINK LOST"}</span>
          </div>
          <div className="clock">{now ? now.toLocaleTimeString([], { hour12: false }) : "--:--:--"}</div>
        </div>
      </aside>
      <main className={`main${isHero ? " main-hero" : ""}`}>{children}</main>
    </div>
  );
}
