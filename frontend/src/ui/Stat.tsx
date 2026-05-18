export default function Stat({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="border-l border-line pl-3">
      <div className="caption">{label}</div>
      <div className="mt-1 font-mono text-base tabular-nums text-ink">
        {value}
      </div>
    </div>
  );
}
