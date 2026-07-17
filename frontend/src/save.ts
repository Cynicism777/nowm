import { downloadZip, type ImageItem } from "./api";

function pngName(im: ImageItem): string {
  const base = im.file_id.split("/").pop() || `image_${im.index + 1}`;
  return `${base}.png`;
}

async function fetchAsFile(im: ImageItem): Promise<File> {
  const r = await fetch(im.url);
  if (!r.ok) throw new Error("图片获取失败");
  const blob = await r.blob();
  return new File([blob], pngName(im), { type: blob.type || "image/png" });
}

function canShareFiles(files: File[]): boolean {
  return (
    typeof navigator !== "undefined" &&
    typeof navigator.canShare === "function" &&
    navigator.canShare({ files })
  );
}

export function supportsFileShare(): boolean {
  if (typeof navigator === "undefined" || typeof navigator.canShare !== "function") {
    return false;
  }
  try {
    const probe = new File([new Blob([""], { type: "image/png" })], "probe.png", {
      type: "image/png",
    });
    return navigator.canShare({ files: [probe] });
  } catch {
    return false;
  }
}

function downloadBlob(blob: Blob, filename: string): void {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

function isAbort(e: unknown): boolean {
  return e instanceof Error && e.name === "AbortError";
}

export async function saveOne(im: ImageItem): Promise<void> {
  const file = await fetchAsFile(im);
  if (canShareFiles([file])) {
    try {
      await navigator.share({ files: [file] });
      return;
    } catch (e) {
      if (isAbort(e)) return;
    }
  }
  downloadBlob(file, file.name);
}

export type SaveAllResult = { kind: "shared" | "zip" | "guide" };

export async function saveAll(images: ImageItem[], title: string): Promise<SaveAllResult> {
  if (supportsFileShare()) {
    const files = await Promise.all(images.map(fetchAsFile));
    if (canShareFiles(files)) {
      try {
        await navigator.share({ files, title });
      } catch (e) {
        if (!isAbort(e)) throw e;
      }
      return { kind: "shared" };
    }
    return { kind: "guide" };
  }
  await downloadZip(
    images.map((i) => i.file_id),
    title,
  );
  return { kind: "zip" };
}
