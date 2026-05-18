// Shimmer placeholder for loading states.

export default function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div
      className={`relative overflow-hidden rounded-xl bg-slate-100 ${className}`}
    >
      <div className="absolute inset-0 -translate-x-full animate-shimmer
        bg-gradient-to-r from-transparent via-white/60 to-transparent" />
    </div>
  );
}
