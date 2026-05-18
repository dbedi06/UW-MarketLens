import { motion } from "framer-motion";
import { fadeUp } from "../lib/motion";

export default function Card({
  children,
  className = "",
  hover = false,
  as = "div",
}: {
  children: React.ReactNode;
  className?: string;
  hover?: boolean;
  as?: "div" | "section";
}) {
  const Comp = motion[as];
  return (
    <Comp
      variants={fadeUp}
      whileHover={hover ? { borderColor: "#1A1714" } : undefined}
      className={`card p-6 ${className}`}
    >
      {children}
    </Comp>
  );
}
