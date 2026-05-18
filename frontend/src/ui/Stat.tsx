export default function Stat({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-xl bg-slate-50 ring-1 ring-slate-200/70 px-4 py-3">
      <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
        {label}
      </div>
      <div className="mt-0.5 font-display text-lg font-semibold text-brand-700">
        {value}
      </div>
    </div>
  );
}
