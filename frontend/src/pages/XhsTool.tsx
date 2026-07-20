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
    <div className="paper-app">
      <header className="topbar">
        <Link to="/" className="back">‹ 返回</Link>
        <h1 className="page-title">小红书无水印</h1>
      </header>
      <div className="sheet">
        <div className="parse-row">
          <input
            className="field"
            value={share}
            onChange={(e) => setShare(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && onParse()}
            placeholder="粘贴小红书分享链接或文案"
          />
          <button className="btn" onClick={onParse} disabled={loading}>
            {loading ? "解析中…" : "解析"}
          </button>
        </div>

        {err && <p className="err">{err}</p>}

        {note && (
          <>
            <div className="result-head">
              <div className="result-meta">
                <div className="result-title">{note.title}</div>
                <div className="result-sub">
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
          </>
        )}
      </div>
    </div>
  );
}
