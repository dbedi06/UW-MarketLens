// Shared Framer Motion variants. Durations kept ≤ .5s; Framer automatically
// respects prefers-reduced-motion when useReducedMotion()/MotionConfig is used,
// and our global CSS rule also collapses transitions as a safety net.

import type { Variants } from "framer-motion";

// Bold Swiss: present, confident motion (not the over-calm editorial pass,
// not the old fade-everything). Still reduced-motion safe.
export const fadeUp: Variants = {
  hidden: { opacity: 0, y: 18 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] },
  },
};

export const fadeIn: Variants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { duration: 0.4 } },
};

export const stagger: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.07, delayChildren: 0.04 } },
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
