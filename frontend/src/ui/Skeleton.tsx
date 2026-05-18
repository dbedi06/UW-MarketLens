// Quiet loading placeholder — a soft pulse on the hairline tone (no shimmer
// gradient; editorial calm).

export default function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div className={`animate-pulse rounded-md bg-line/60 ${className}`} />
  );
}
