import { motion, useReducedMotion } from "framer-motion";
import type { ReactNode } from "react";

export default function Pressable(
  { children, onClick, className }:
  { children: ReactNode; onClick?: () => void; className?: string }
) {
  const reduced = useReducedMotion();
  return (
    <motion.div
      className={className}
      onClick={onClick}
      whileTap={reduced ? {} : { scale: 0.97 }}
      transition={{ type: "spring", bounce: 0, duration: 0.25 }}
      style={{ display: "inline-block", cursor: onClick ? "pointer" : "default" }}
    >
      {children}
    </motion.div>
  );
}
