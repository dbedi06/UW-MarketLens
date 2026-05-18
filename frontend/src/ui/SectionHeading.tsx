export default function SectionHeading({
  eyebrow,
  title,
  sub,
}: {
  eyebrow?: string;
  title: string;
  sub?: string;
}) {
  return (
    <div className="mb-4">
      {eyebrow && <div className="eyebrow mb-1.5">{eyebrow}</div>}
      <h2 className="text-xl font-semibold">{title}</h2>
      {sub && <p className="mt-1 text-sm text-slate-500">{sub}</p>}
    </div>
  );
}
