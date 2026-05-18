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
    <div className="mb-5">
      {eyebrow && <div className="caption mb-2">{eyebrow}</div>}
      <h2 className="section-title">{title}</h2>
      {sub && <p className="mt-1.5 max-w-prose text-sm text-ink/55">{sub}</p>}
    </div>
  );
}
