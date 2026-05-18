import { motion } from "framer-motion";

type Variant = "primary" | "ghost";

export default function Button({
  children,
  variant = "primary",
  className = "",
  ...rest
}: {
  children: React.ReactNode;
  variant?: Variant;
  className?: string;
} & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <motion.button
      whileTap={{ scale: 0.97 }}
      className={`${variant === "primary" ? "btn-primary" : "btn-ghost"} ${className}`}
      {...(rest as React.ComponentProps<typeof motion.button>)}
    >
      {children}
    </motion.button>
  );
}
