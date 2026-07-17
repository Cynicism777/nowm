import { useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import type { ImageItem } from "../api";
import { saveOne, supportsFileShare } from "../save";

export default function ImageGrid({ images }: { images: ImageItem[] }) {
  const reduced = useReducedMotion();
  const shareLabel = supportsFileShare() ? "保存" : "下载";
  const [busy, setBusy] = useState<string | null>(null);

  async function onSave(im: ImageItem) {
    if (busy) return;
    setBusy(im.file_id);
    try {
      await saveOne(im);
    } catch {
      // 保存失败静默（saveOne 内已尽力回退下载）
    } finally {
      setBusy(null);
    }
  }

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
          <button
            onClick={() => onSave(im)}
            disabled={busy === im.file_id}
            style={{ position: "absolute", right: 8, bottom: 8, border: "none",
                     background: "rgba(0,0,0,0.55)", color: "#fff", cursor: "pointer",
                     borderRadius: 980, padding: "6px 12px", fontSize: 13,
                     backdropFilter: "blur(6px)" }}>
            {busy === im.file_id ? "…" : shareLabel}
          </button>
        </motion.div>
      ))}
    </div>
  );
}
