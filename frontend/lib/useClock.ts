"use client";

import { useEffect, useState } from "react";

/** Ticks once per second; returns null until mounted (avoids SSR/client clock mismatch). */
export function useClock() {
  const [now, setNow] = useState<Date | null>(null);
  useEffect(() => {
    setNow(new Date());
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);
  return now;
}
