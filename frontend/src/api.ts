// Single place that knows where the backend lives. To point at staging/prod
// later, change BASE (or wire it to an env var) — no component changes needed.

import type { MarketScore, LibraryEntry, PendingTag } from "./types";

const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

// Absolute URL of the dynamic OG share card for a snapshot id.
export function ogImageUrl(id: string): string {
  return `${BASE}/api/og/${id}`;
}

async function jsonOrThrow<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Request failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}

export function getScore(url: string, asOf?: string): Promise<MarketScore> {
  return fetch(`${BASE}/api/score`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, as_of: asOf ?? null }),
  }).then((r) => jsonOrThrow<MarketScore>(r));
}

export function getSnapshot(id: string): Promise<MarketScore> {
  return fetch(`${BASE}/api/snapshot/${id}`).then((r) =>
    jsonOrThrow<MarketScore>(r),
  );
}

export function getLibrary(
  q?: string,
  dept?: string,
): Promise<LibraryEntry[]> {
  const p = new URLSearchParams();
  if (q) p.set("q", q);
  if (dept) p.set("dept", dept);
  const qs = p.toString();
  return fetch(`${BASE}/api/library${qs ? `?${qs}` : ""}`).then((r) =>
    jsonOrThrow<LibraryEntry[]>(r),
  );
}

export function getPendingTags(): Promise<PendingTag[]> {
  return fetch(`${BASE}/api/admin/pending-tags`).then((r) =>
    jsonOrThrow<PendingTag[]>(r),
  );
}

export function verifyTag(
  market_url: string,
  action: "approve" | "override",
  departments?: string[],
): Promise<PendingTag> {
  return fetch(`${BASE}/api/admin/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ market_url, action, departments: departments ?? null }),
  }).then((r) => jsonOrThrow<PendingTag>(r));
}
