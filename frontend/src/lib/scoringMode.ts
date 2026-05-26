// Scoring mode: which backend route the lookup pages hit.
//
//   "live"  → POST /api/live/score   real Polymarket ingestion + S1→S2→S3.
//             The detector is synthetic-trained; numbers are directional,
//             not authoritative. Cache miss → 503 (prompt user to switch).
//   "mock"  → POST /api/score        deterministic mock; always works.
//
// Persisted in localStorage so toggling survives a reload. Default is
// "live" — exposes the real pipeline up front; "mock" is the safety net.

import { useCallback, useEffect, useState } from "react";

export type ScoringMode = "live" | "mock";

const KEY = "marketlens.scoringMode";
const DEFAULT: ScoringMode = "live";
const EVENT = "marketlens:scoring-mode-changed";

function read(): ScoringMode {
  if (typeof window === "undefined") return DEFAULT;
  const v = window.localStorage.getItem(KEY);
  return v === "mock" ? "mock" : "live";
}

export function useScoringMode(): {
  mode: ScoringMode;
  setMode: (m: ScoringMode) => void;
  toggle: () => void;
} {
  const [mode, setLocalMode] = useState<ScoringMode>(read);

  useEffect(() => {
    function onChange() {
      setLocalMode(read());
    }
    window.addEventListener(EVENT, onChange);
    window.addEventListener("storage", onChange);
    return () => {
      window.removeEventListener(EVENT, onChange);
      window.removeEventListener("storage", onChange);
    };
  }, []);

  const setMode = useCallback((m: ScoringMode) => {
    window.localStorage.setItem(KEY, m);
    window.dispatchEvent(new Event(EVENT));
    setLocalMode(m);
  }, []);

  const toggle = useCallback(() => {
    setMode(read() === "live" ? "mock" : "live");
  }, [setMode]);

  return { mode, setMode, toggle };
}
