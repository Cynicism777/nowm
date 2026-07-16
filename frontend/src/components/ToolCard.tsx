import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";

export default function ToolCard(
  { title, desc, to }: { title: string; desc: string; to: string }
) {
  const nav = useNavigate();
  return (
    <motion.button
      onClick={() => nav(to)}
      whileHover={{ y: -4 }}
      whileTap={{ scale: 0.98 }}
      transition={{ type: "spring", bounce: 0, duration: 0.3 }}
      style={{
        textAlign: "left", border: "none", cursor: "pointer",
        background: "#fff", borderRadius: "var(--radius)", padding: 22,
        boxShadow: "0 6px 24px rgba(0,0,0,0.06)", width: "100%",
      }}
    >
      <div style={{ fontSize: 18, fontWeight: 600, marginBottom: 6 }}>{title}</div>
      <div style={{ color: "var(--muted)", fontSize: 14 }}>{desc}</div>
    </motion.button>
  );
}
