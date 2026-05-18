// Page wrapper: max width, padding, and a subtle mount animation. Wrap each
// page's content so transitions are consistent app-wide.

import { motion } from "framer-motion";
import { stagger } from "../lib/motion";

export default function PageShell({
  children,
  wide = false,
}: {
  children: React.ReactNode;
  wide?: boolean;
}) {
  return (
    <motion.div
      variants={stagger}
      initial="hidden"
      animate="show"
      className={`mx-auto w-full px-5 sm:px-8 lg:px-14 py-10 ${
        wide ? "max-w-content" : "max-w-prose"
      }`}
    >
      {children}
    </motion.div>
  );
}
