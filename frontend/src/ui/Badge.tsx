// Pills for bands, severities, and verified state. Gold is reserved for
// "reliable/verified" wins only — used sparingly per the brand rule.

type Tone = "good" | "warn" | "bad" | "brand" | "gold" | "neutral";

// Flat editorial tags: hairline border + ink/semantic text, no fill/glow.
const TONES: Record<Tone, string> = {
  good: "border-good/40 text-good",
  warn: "border-warn/40 text-warn",
  bad: "border-bad/40 text-bad",
  brand: "border-brand-600/40 text-brand-700",
  gold: "border-gold/50 text-gold-text",
  neutral: "border-line text-ink/60",
};

export function bandTone(band: string): Tone {
  return band === "HIGH" ? "good" : band === "MEDIUM" ? "warn" : "bad";
}

export default function Badge({
  children,
  tone = "neutral",
  className = "",
}: {
  children: React.ReactNode;
  tone?: Tone;
  className?: string;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-sm border px-2 py-0.5
        font-mono text-[11px] font-medium uppercase tracking-wide
        ${TONES[tone]} ${className}`}
    >
      {children}
    </span>
  );
}
