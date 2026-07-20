import { useNavigate } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";

export default function ToolCard(
  { title, desc, to }: { title: string; desc: string; to: string }
) {
  const nav = useNavigate();
  const reduced = useReducedMotion();
  return (
    <motion.button
      type="button"
      className="tool-card"
      onClick={() => nav(to)}
      whileHover={reduced ? {} : { y: -3 }}
      whileTap={reduced ? {} : { scale: 0.985 }}
      transition={{ type: "spring", bounce: 0, duration: 0.3 }}
    >
      <span className="tool-card__title">{title}</span>
      <span className="tool-card__desc">{desc}</span>
    </motion.button>
  );
}
