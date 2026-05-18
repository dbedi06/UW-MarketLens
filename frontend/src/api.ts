// Single place that knows where the backend lives. To point at staging/prod
// later, change BASE (or wire it to an env var) — no component changes needed.

import type { MarketScore, LibraryEntry } from "./types";

const BASE = "http://localhost:8000";

async function jsonOrThrow<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Request failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}

export function getScore(url: string): Promise<MarketScore> {
  return fetch(`${BASE}/api/score`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  }).then((r) => jsonOrThrow<MarketScore>(r));
}

export function getLibrary(): Promise<LibraryEntry[]> {
  return fetch(`${BASE}/api/library`).then((r) => jsonOrThrow<LibraryEntry[]>(r));
}
