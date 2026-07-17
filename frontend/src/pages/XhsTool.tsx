import { useState } from "react";
import { Link } from "react-router-dom";
import { parseShare, type NoteResp } from "../api";
import ImageGrid from "../components/ImageGrid";
import { saveAll, supportsFileShare } from "../save";

export default function XhsTool() {
  const [share, setShare] = useState("");
  const [note, setNote] = useState<NoteResp | null>(null);
  const [loading, setLoading] = useState(false);
  const [zipping, setZipping] = useState(false);
  const [err, setErr] = useState("");

  async function onParse() {
    if (!share.trim() || loading) return;
    setLoading(true); setErr(""); setNote(null);
    try {
      setNote(await parseShare(share));
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  const canShare = supportsFileShare();

  async function onSaveAll() {
    if (!note || zipping) return;
    setZipping(true); setErr("");
    try {
      const res = await saveAll(note.images, note.title);
      if (res.kind === "guide") {
        setErr("此设备暂不支持批量存相册，请用每张图片上的「保存」按钮逐张存到相册");
      }
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setZipping(false);
    }
  }

  return (
    <>
      <div className="toolbar" style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <Link to="/" style={{ textDecoration: "none", color: "var(--accent)" }}>‹ 返回</Link>
        <h1 style={{ fontSize: 20, margin: 0 }}>小红书无水印下载</h1>
      </div>
      <div className="container">
        <div style={{ display: "flex", gap: 10 }}>
          <input
            value={share}
            onChange={(e) => setShare(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && onParse()}
            placeholder="粘贴小红书分享链接或文案"
            style={{ flex: 1, padding: "12px 16px", borderRadius: 12,
                     border: "1px solid #d2d2d7", fontSize: 15 }}
          />
          <button className="btn" onClick={onParse} disabled={loading}>
            {loading ? "解析中…" : "解析"}
          </button>
        </div>

        {err && <p style={{ color: "#d70015", marginTop: 14 }}>{err}</p>}

        {note && (
          <div style={{ marginTop: 22 }}>
            <div style={{ display: "flex", justifyContent: "space-between",
                          alignItems: "center", marginBottom: 14, gap: 12 }}>
              <div style={{ minWidth: 0 }}>
                <div style={{ fontWeight: 600, whiteSpace: "nowrap",
                              overflow: "hidden", textOverflow: "ellipsis" }}>
                  {note.title}
                </div>
                <div style={{ color: "var(--muted)", fontSize: 13 }}>
                  @{note.author} · {note.images.length} 张
                </div>
              </div>
              <button className="btn" onClick={onSaveAll} disabled={zipping}>
                {zipping
                  ? (canShare ? "保存中…" : "打包中…")
                  : (canShare ? "保存全部" : "打包下载 ZIP")}
              </button>
            </div>
            <ImageGrid images={note.images} />
          </div>
        )}
      </div>
    </>
  );
}
