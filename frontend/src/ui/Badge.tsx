// Pills for bands, severities, and verified state. Gold is reserved for
// "reliable/verified" wins only — used sparingly per the brand rule.

type Tone = "good" | "warn" | "bad" | "brand" | "gold" | "neutral";

const TONES: Record<Tone, string> = {
  good: "bg-good/10 text-good ring-good/20",
  warn: "bg-warn/10 text-warn ring-warn/20",
  bad: "bg-bad/10 text-bad ring-bad/20",
  brand: "bg-brand-600/10 text-brand-700 ring-brand-600/20",
  gold: "bg-gold/15 text-gold-text ring-gold/30",
  neutral: "bg-slate-100 text-slate-600 ring-slate-200",
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
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1
        text-xs font-semibold ring-1 ring-inset ${TONES[tone]} ${className}`}
    >
      {children}
    </span>
  );
}
