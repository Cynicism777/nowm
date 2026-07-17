# 图片保存自适应（手机存相册 / PC 下载）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让「保存图片/打包下载」按设备能力自适应——手机走系统分享面板存相册、PC 走文件/ZIP 下载，UI 只有一套响应式。

**Architecture:** 新增前端保存策略层 `frontend/src/save.ts`，把设备差异全部收敛其中；UI 组件仅调用 `saveOne/saveAll` 并按能力探测切换文案。后端仅补 uvicorn 反向代理配置。所有能力探测基于 `navigator.canShare({files})`，非安全上下文自动回退下载。

**Tech Stack:** React 18 + TypeScript + Vite；Web Share API；后端 uvicorn。

## Global Constraints

- 仓库根目录为 `nowm/`，路径以此为根；不引用外层 `media/` 目录。
- 设备差异只允许存在于 `frontend/src/save.ts`；`ImageGrid`/`XhsTool` 除文案外不含设备条件分支。
- 后端 API 不变（`/api/parse`、`/api/image`、`/api/package` 保持现签名）。
- HTTPS 由用户既有网关终结，仓库不管证书；后端 `uvicorn` 加 `--proxy-headers --forwarded-allow-ips=*`。
- 前端沿用仓库现状「构建 + 手动端到端」验证，不引入前端单测框架。
- 保持 Apple 风格现有交互，不新增视觉元素。
- 提交信息不写 `Co-authored-by`。

---

## File Structure

```
frontend/src/
  save.ts                      # 新增：保存策略层（能力探测 + 分享/下载分支）
  api.ts                       # 不变（saveAll 复用 downloadZip）
  components/ImageGrid.tsx     # 改：单图按钮改调 saveOne，文案自适应
  pages/XhsTool.tsx            # 改：批量按钮改调 saveAll，处理 guide 提示
Dockerfile                     # 改：CMD 增加 --proxy-headers --forwarded-allow-ips=*
README.md                      # 改：补 HTTPS 硬约束说明
```

---

## Task 1: 新增保存策略层 `save.ts`

**Files:**
- Create: `frontend/src/save.ts`

**Interfaces:**
- Consumes: `api.ts` 的 `downloadZip(fileIds: string[], title: string): Promise<void>` 与类型 `ImageItem { index; file_id; width; height; url }`。
- Produces:
  - `supportsFileShare(): boolean`
  - `saveOne(im: ImageItem): Promise<void>`
  - `type SaveAllResult = { kind: "shared" | "zip" | "guide" }`
  - `saveAll(images: ImageItem[], title: string): Promise<SaveAllResult>`

- [ ] **Step 1: 写 `frontend/src/save.ts`**

```ts
import { downloadZip, type ImageItem } from "./api";

function pngName(im: ImageItem): string {
  const base = im.file_id.split("/").pop() || `image_${im.index + 1}`;
  return `${base}.png`;
}

async function fetchAsFile(im: ImageItem): Promise<File> {
  // 同源代理，且图片已在页面展示，通常命中 HTTP 缓存 → 快，保住分享的用户激活窗口
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

// 探测是否支持“文件分享”（决定 UI 文案与分支）：需安全上下文 + canShare
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
      if (isAbort(e)) return; // 用户取消，视为正常
      // 其它错误 → 回退下载
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
        if (!isAbort(e)) throw e; // 取消当成功，其它错误上抛
      }
      return { kind: "shared" };
    }
    // 支持单图分享但不支持多图（罕见）→ 引导逐张保存
    return { kind: "guide" };
  }
  // PC / 不支持文件分享 → 打包 ZIP
  await downloadZip(
    images.map((i) => i.file_id),
    title,
  );
  return { kind: "zip" };
}
```

- [ ] **Step 2: 构建验证类型正确**

Run: `cd frontend && npm run build`
Expected: 构建成功，无 TS 错误（`save.ts` 纳入编译）。

- [ ] **Step 3: Commit**

```bash
cd /mnt/disk1/cynic/mntlab/media/nowm
git add frontend/src/save.ts
git commit -m "feat(frontend): 新增保存策略层 save.ts（能力探测：分享存相册/下载）"
```

---

## Task 2: `ImageGrid` 单图按钮改用 `saveOne`

**Files:**
- Modify: `frontend/src/components/ImageGrid.tsx`

**Interfaces:**
- Consumes: `save.ts` 的 `saveOne`, `supportsFileShare`；`api.ts` 的 `ImageItem`。
- Produces: 无新导出（组件内部行为变化）。

- [ ] **Step 1: 重写 `frontend/src/components/ImageGrid.tsx`**

```tsx
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
```

- [ ] **Step 2: 构建验证**

Run: `cd frontend && npm run build`
Expected: 构建成功，无 TS 错误。

- [ ] **Step 3: Commit**

```bash
cd /mnt/disk1/cynic/mntlab/media/nowm
git add frontend/src/components/ImageGrid.tsx
git commit -m "feat(frontend): 单图按钮改用 saveOne，手机存相册/PC 下载自适应"
```

---

## Task 3: `XhsTool` 批量按钮改用 `saveAll`

**Files:**
- Modify: `frontend/src/pages/XhsTool.tsx`

**Interfaces:**
- Consumes: `save.ts` 的 `saveAll`, `supportsFileShare`；`api.ts` 的 `parseShare`, `NoteResp`。
  （不再直接 import `downloadZip`；改由 `saveAll` 内部调用。）
- Produces: 无新导出。

- [ ] **Step 1: 改 import 行**

把：

```tsx
import { parseShare, downloadZip, type NoteResp } from "../api";
import ImageGrid from "../components/ImageGrid";
```

改为：

```tsx
import { parseShare, type NoteResp } from "../api";
import ImageGrid from "../components/ImageGrid";
import { saveAll, supportsFileShare } from "../save";
```

- [ ] **Step 2: 替换 `onZip` 为 `onSaveAll`**

把：

```tsx
  async function onZip() {
    if (!note || zipping) return;
    setZipping(true);
    try {
      await downloadZip(note.images.map((i) => i.file_id), note.title);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setZipping(false);
    }
  }
```

改为：

```tsx
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
```

- [ ] **Step 3: 替换批量按钮的 onClick 与文案**

把：

```tsx
              <button className="btn" onClick={onZip} disabled={zipping}>
                {zipping ? "打包中…" : "打包下载全部"}
              </button>
```

改为：

```tsx
              <button className="btn" onClick={onSaveAll} disabled={zipping}>
                {zipping
                  ? (canShare ? "保存中…" : "打包中…")
                  : (canShare ? "保存全部" : "打包下载 ZIP")}
              </button>
```

- [ ] **Step 4: 构建验证**

Run: `cd frontend && npm run build`
Expected: 构建成功，无 TS 错误（确认 `downloadZip` 已无未使用告警——它仍被 `save.ts` 使用）。

- [ ] **Step 5: Commit**

```bash
cd /mnt/disk1/cynic/mntlab/media/nowm
git add frontend/src/pages/XhsTool.tsx
git commit -m "feat(frontend): 批量按钮改用 saveAll，手机分享存相册/PC 打包 ZIP"
```

---

## Task 4: 后端反向代理配置与文档

**Files:**
- Modify: `Dockerfile`（`CMD` 行）
- Modify: `README.md`（补 HTTPS 说明）

**Interfaces:**
- Consumes: 无。
- Produces: 无（部署/文档变更）。

- [ ] **Step 1: 改 `Dockerfile` 的 CMD**

把：

```dockerfile
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

改为：

```dockerfile
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--proxy-headers", "--forwarded-allow-ips", "*"]
```

- [ ] **Step 2: 在 `README.md` 增补 HTTPS 说明段落**

在部署/快速开始相关位置追加一段（措辞可按 README 现状微调）：

```markdown
## HTTPS 与手机存相册

手机端「保存到相册」依赖浏览器 Web Share API，该 API 仅在**安全上下文（HTTPS）**下可用。
本服务默认由你的网关/反向代理统一终结 HTTPS，容器内保持 HTTP（`--proxy-headers` 已开启，
可正确识别转发协议与客户端 IP）。

- 经 HTTPS 访问：手机点「保存」/「保存全部」会弹系统分享面板，可直接存入相册。
- 经明文 HTTP 访问：自动回退为文件下载 / ZIP 下载，功能不受影响，但无法直接存相册。
```

- [ ] **Step 3: 构建并冒烟验证**

Run: `docker compose up -d --build`
Run: `curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8823/`
Expected: `200`。
Run: `docker compose logs --tail 20 nowm`
Expected: uvicorn 启动无报错（含 proxy-headers 生效，无异常）。

- [ ] **Step 4: Commit**

```bash
cd /mnt/disk1/cynic/mntlab/media/nowm
git add Dockerfile README.md
git commit -m "chore: uvicorn 开启 proxy-headers 并补充 HTTPS/存相册说明"
```

---

## Task 5: 端到端手动验证

**Files:** 无（验证任务）。

- [ ] **Step 1: PC 浏览器验证（HTTP 即可）**

打开 `http://<服务器IP>:8823/xhs`，粘贴有效分享链接解析：
- 单图按钮显示「下载」，点击下载得到 png。
- 批量按钮显示「打包下载 ZIP」，点击得到 zip。

- [ ] **Step 2: 手机验证（需经网关 HTTPS 访问）**

手机浏览器打开 `https://<网关域名>/xhs`，解析后：
- 单图按钮显示「保存」，点击弹系统分享面板，可存到相册。
- 批量按钮显示「保存全部」，点击一次弹面板，可批量存相册（iOS Safari / Android Chrome）。
- 用户在面板取消 → 页面无报错。

- [ ] **Step 3: 明文 HTTP 回退验证（手机）**

手机经 `http://<IP>:8823/` 打开：按钮显示「下载」/「打包下载 ZIP」，功能正常不报错（自动回退）。

---

## Self-Review

**1. Spec coverage:**
- 保存策略层收敛设备差异 → Task 1 `save.ts` ✓
- 手机单张/批量存相册、PC 下载/ZIP → Task 1 分支 + Task 2/3 UI ✓
- UI 只文案分支、无设备条件逻辑 → Task 2/3 仅用 `supportsFileShare()` 切文案 ✓
- 多图不支持时引导逐张（不下载）→ Task 1 返回 `guide` + Task 3 提示 ✓
- 非安全上下文自动回退 → Task 1 `supportsFileShare` 为 false 走下载/ZIP ✓
- 用户取消分享不报错 → Task 1 `isAbort` 处理 ✓
- 后端 proxy-headers → Task 4 ✓
- HTTPS 硬约束文档 → Task 4 README ✓
- 端到端（PC/手机/HTTP 回退）→ Task 5 ✓

**2. Placeholder scan:** 无 TBD/TODO；所有代码步骤含完整代码，改动步骤给出原文与替换文。

**3. Type consistency:**
- `ImageItem`（`index/file_id/width/height/url`）来自现有 `api.ts`，Task 1/2 一致使用。
- `downloadZip(fileIds, title)` 现有签名，Task 1 `saveAll` 调用一致。
- `saveOne(im): Promise<void>`、`saveAll(images, title): Promise<SaveAllResult>`、
  `supportsFileShare(): boolean` 在 Task 1 定义，Task 2/3 调用一致。
- `SaveAllResult.kind` 取值 `shared|zip|guide`，Task 3 仅判断 `guide`，一致。
