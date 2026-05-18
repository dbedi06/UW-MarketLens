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
      whileHover={hover ? { y: -3, boxShadow: "0 8px 30px rgba(75,46,131,.12)" } : undefined}
      className={`card p-6 ${className}`}
    >
      {children}
    </Comp>
  );
}
