// Shared Framer Motion variants. Durations kept ≤ .5s; Framer automatically
// respects prefers-reduced-motion when useReducedMotion()/MotionConfig is used,
// and our global CSS rule also collapses transitions as a safety net.

import type { Variants } from "framer-motion";

export const fadeUp: Variants = {
  hidden: { opacity: 0, y: 16 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.45, ease: [0.22, 1, 0.36, 1] },
  },
};

export const fadeIn: Variants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { duration: 0.4 } },
};

export const stagger: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08, delayChildren: 0.05 } },
};

// Drop-in props for scroll-reveal sections.
export const reveal = {
  variants: fadeUp,
  initial: "hidden" as const,
  whileInView: "show" as const,
  viewport: { once: true, amount: 0.25 },
};

// Page transition used by <AnimatePresence> in App.tsx.
export const pageTransition = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -8 },
  transition: { duration: 0.28, ease: "easeOut" as const },
};
