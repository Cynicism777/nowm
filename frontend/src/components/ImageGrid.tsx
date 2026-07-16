import { motion, useReducedMotion } from "framer-motion";
import type { ImageItem } from "../api";

export default function ImageGrid({ images }: { images: ImageItem[] }) {
  const reduced = useReducedMotion();
  return (
    <div style={{ display: "grid", gridTemplateColumns:
      "repeat(auto-fill, minmax(150px, 1fr))", gap: 12 }}>
      {images.map((im, i) => (
        <motion.div
          key={im.file_id}
          initial={reduced ? { opacity: 0 } : { opacity: 0, y: 12 }}
          animate={reduced ? { opacity: 1 } : { opacity: 1, y: 0 }}
          transition={{ type: "spring", bounce: 0, duration: 0.4, delay: reduced ? 0 : i * 0.03 }}
          style={{ position: "relative", borderRadius: 14, overflow: "hidden",
                   background: "#e8e8ed", aspectRatio: "3/4" }}
        >
          <img src={im.url} loading="lazy" alt=""
               style={{ width: "100%", height: "100%", objectFit: "cover" }} />
          <a href={`${im.url}&download=1`}
             style={{ position: "absolute", right: 8, bottom: 8,
                      background: "rgba(0,0,0,0.55)", color: "#fff",
                      borderRadius: 980, padding: "6px 12px", fontSize: 13,
                      textDecoration: "none", backdropFilter: "blur(6px)" }}>
            下载
          </a>
        </motion.div>
      ))}
    </div>
  );
}
