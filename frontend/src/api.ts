export interface ImageItem {
  index: number; file_id: string; width: number; height: number; url: string;
}
export interface NoteResp {
  note_id: string; title: string; author: string; images: ImageItem[];
}

export async function parseShare(share: string): Promise<NoteResp> {
  const r = await fetch("/api/parse", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ share }),
  });
  if (!r.ok) {
    const detail = await r.json().catch(() => ({ detail: "解析失败" }));
    throw new Error(detail.detail || "解析失败");
  }
  return r.json();
}

export async function downloadZip(fileIds: string[], title: string) {
  const r = await fetch("/api/package", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ file_ids: fileIds, title }),
  });
  if (!r.ok) {
    const detail = await r.json().catch(() => ({ detail: "打包失败" }));
    throw new Error(detail.detail || "打包失败");
  }
  const blob = await r.blob();
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `${title}.zip`;
  a.click();
  URL.revokeObjectURL(a.href);
}
