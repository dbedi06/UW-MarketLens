// Accessible native date control, styled to the system.

export default function DateField({
  label,
  value,
  max,
  onChange,
}: {
  label: string;
  value: string;
  max?: string;
  onChange: (v: string) => void;
}) {
  return (
    <label className="flex items-center gap-2.5">
      <span className="caption">{label}</span>
      <input
        type="date"
        value={value}
        max={max}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-lg border border-line bg-panel px-3 py-1.5
          font-mono text-xs text-ink focus:border-brand-600
          focus:ring-2 focus:ring-brand-600/20"
      />
    </label>
  );
}
