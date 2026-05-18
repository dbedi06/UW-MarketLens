// Accessible explainer: a focusable button that reveals a description on
// hover and focus, dismissable with Escape. Replaces title-only tooltips.

import { useId, useState } from "react";

export default function InfoTip({ text }: { text: string }) {
  const [open, setOpen] = useState(false);
  const id = useId();

  return (
    <span className="relative inline-block">
      <button
        type="button"
        aria-label="Explain this metric"
        aria-expanded={open}
        aria-describedby={open ? id : undefined}
        onClick={() => setOpen((o) => !o)}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onKeyDown={(e) => e.key === "Escape" && setOpen(false)}
        className="grid h-4 w-4 place-items-center rounded-full border
          border-ink/30 font-mono text-[10px] leading-none text-ink/50
          hover:border-ink hover:text-ink focus:outline-none
          focus-visible:ring-2 focus-visible:ring-brand-600/40"
      >
        i
      </button>
      {open && (
        <span
          id={id}
          role="tooltip"
          className="absolute left-0 top-6 z-20 w-60 rounded-lg border
            border-line bg-panel p-3 text-xs leading-relaxed text-ink/70
            shadow-soft"
        >
          {text}
        </span>
      )}
    </span>
  );
}
