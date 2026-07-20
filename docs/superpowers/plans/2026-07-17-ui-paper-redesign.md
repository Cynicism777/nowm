# nowm 前端 UI 纸感美化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将正式前端视觉对齐「柔和纸感 + 微纹理」试验场稿，品牌统一为词标 `nowm`，不改任何业务逻辑。

**Architecture:** 在 `frontend/public/` 放入纸纹与 favicon；用 `theme.css` 承载颜色 token、纸面背景与通用控件类；各页面/组件改为使用这些类（少写 inline style），结构对齐 `experiment/index.html`。字体通过 `index.html` 引入 Google Fonts（Syne + Noto Sans SC），并设系统字体回退。

**Tech Stack:** React 18 + TypeScript + Vite；既有 framer-motion；无新增依赖。

## Global Constraints

- 仓库根目录为 `nowm/`；路径以此为根。
- **不改** `api.ts` / `auth.ts` / `save.ts` 业务逻辑；不改后端与 Docker。
- UI 不再出现「cynic 工具箱」整词；主品牌只写 `nowm`。首页副文案为「cynic·百宝箱」（用户已改定）。
- 颜色 / 间距以 `docs/superpowers/specs/2026-07-17-ui-paper-redesign-design.md` 与 `experiment/preview.css` 为准。
- 前端验证方式：`npm run build` + 手动对照试验场；不引入前端单测框架。
- 提交信息不写 `Co-authored-by`；仅在用户要求时 commit。
- `experiment/` 保持 gitignore，不纳入正式构建。

---

## File Structure

```
frontend/
  index.html                 # title、favicon、Google Fonts
  public/
    paper-texture.svg        # 从 experiment 复制
    favicon.svg              # 新建墨色词标缩写
  src/
    theme.css                # token + 纸面 + 通用类（.topbar .btn .field …）
    App.tsx                  # 轻量加载态
    pages/Home.tsx           # 词标首页
    pages/Locked.tsx         # 未授权页
    pages/XhsTool.tsx        # 工具页样式/短标题
    components/ToolCard.tsx  # 纸感卡片类
    components/ImageGrid.tsx # 角标按钮对齐纸感深色
```

---

### Task 1: 静态资源（纸纹 + favicon）

**Files:**
- Create: `frontend/public/paper-texture.svg`
- Create: `frontend/public/favicon.svg`

**Interfaces:**
- Consumes: 无
- Produces: 构建后可访问 `/paper-texture.svg`、`/favicon.svg`

- [ ] **Step 1: 复制纸纹**

将 `experiment/paper-texture.svg` 原样复制到 `frontend/public/paper-texture.svg`（内容保持一致）：

```svg
<svg xmlns="http://www.w3.org/2000/svg" width="280" height="280" viewBox="0 0 280 280">
  <filter id="n">
    <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="4" stitchTiles="stitch"/>
    <feColorMatrix type="matrix" values="
      0 0 0 0 0.55
      0 0 0 0 0.48
      0 0 0 0 0.40
      0 0 0 0.55 0"/>
  </filter>
  <rect width="280" height="280" filter="url(#n)" opacity="0.55"/>
</svg>
```

- [ ] **Step 2: 写 favicon**

创建 `frontend/public/favicon.svg`：

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
  <rect width="32" height="32" rx="8" fill="#2a2824"/>
  <text x="16" y="22" text-anchor="middle"
        font-family="Georgia, 'Times New Roman', serif"
        font-size="16" font-weight="700" fill="#f1ece4">n</text>
</svg>
```

- [ ] **Step 3: 确认文件存在**

Run: `ls -la frontend/public/`

Expected: 看到 `paper-texture.svg` 与 `favicon.svg`

- [ ] **Step 4: Commit（仅当用户要求时）**

```bash
git add frontend/public/paper-texture.svg frontend/public/favicon.svg
git commit -m "$(cat <<'EOF'
chore: add paper texture and favicon assets

EOF
)"
```

---

### Task 2: `index.html` + `theme.css` 视觉地基

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/src/theme.css`（整文件替换为纸感体系）

**Interfaces:**
- Consumes: `/paper-texture.svg`、`/favicon.svg`
- Produces: CSS 类名供后续页面使用：
  - 布局：`paper-app`、`topbar`、`topbar--ghost`、`container`、`hero`、`tools`、`sheet`、`locked`
  - 品牌：`mark`、`mark--sm`、`wordmark`、`wordmark--md`、`hero-line`
  - 控件：`btn`、`field`、`parse-row`、`back`、`page-title`
  - 结果：`result-head`、`result-meta`、`result-title`、`result-sub`、`err`
  - 卡片/图格：`tool-card`、`tool-card__title`、`tool-card__desc`、`img-grid`、`img-thumb`、`img-save`

- [ ] **Step 1: 更新 `frontend/index.html`**

完整替换为：

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
    <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Syne:wght@600;700;800&family=Noto+Sans+SC:wght@400;500;600&display=swap" rel="stylesheet" />
    <title>nowm</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 2: 重写 `frontend/src/theme.css`**

完整替换为：

```css
:root {
  --bg: #f1ece4;
  --bg-deep: #e8e1d6;
  --ink: #2a2824;
  --muted: #7a746a;
  --surface: rgba(255, 252, 247, 0.78);
  --surface-solid: #fffdf9;
  --line: rgba(42, 40, 36, 0.08);
  --accent: #2f4a6e;
  --accent-hover: #243a58;
  --danger: #b42318;
  --radius: 20px;
  --shadow: 0 10px 30px rgba(42, 40, 36, 0.07);
  --font-ui: "Noto Sans SC", "PingFang SC", "Microsoft YaHei",
             -apple-system, BlinkMacSystemFont, sans-serif;
  --font-mark: "Syne", "Noto Sans SC", sans-serif;
}

* { box-sizing: border-box; }

html, body {
  margin: 0;
  min-height: 100%;
  color: var(--ink);
  background: var(--bg);
  font: 15px/1.5 var(--font-ui);
  -webkit-font-smoothing: antialiased;
}

body { min-height: 100dvh; }

/* 纸面底：挂在页面根壳上 */
.paper-app {
  position: relative;
  min-height: 100dvh;
  overflow-x: hidden;
  background:
    radial-gradient(1200px 600px at 50% -10%, rgba(255, 255, 255, 0.55), transparent 60%),
    radial-gradient(800px 500px at 100% 100%, rgba(200, 180, 150, 0.18), transparent 55%),
    linear-gradient(180deg, var(--bg) 0%, var(--bg-deep) 100%);
}

.paper-app::before {
  content: "";
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  opacity: 0.45;
  mix-blend-mode: multiply;
  background-image: url("/paper-texture.svg");
  background-size: 280px 280px;
}

.paper-app > * { position: relative; z-index: 1; }

.topbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 22px;
  background: var(--surface);
  backdrop-filter: saturate(140%) blur(18px);
  border-bottom: 1px solid var(--line);
}

.topbar--ghost {
  background: transparent;
  backdrop-filter: none;
  border-bottom: none;
}

.mark {
  font-family: var(--font-mark);
  font-weight: 700;
  letter-spacing: -0.04em;
}

.mark--sm {
  font-size: 15px;
  opacity: 0.72;
}

.page-title {
  margin: 0;
  font-size: 17px;
  font-weight: 600;
  letter-spacing: -0.01em;
}

.back {
  text-decoration: none;
  color: var(--accent);
  font: 500 15px/1 var(--font-ui);
}

.container {
  max-width: 980px;
  margin: 0 auto;
  padding: 20px;
}

.hero {
  padding: 72px 24px 28px;
  text-align: center;
}

.wordmark {
  margin: 0;
  font-family: var(--font-mark);
  font-weight: 800;
  font-size: clamp(4.2rem, 16vw, 7rem);
  letter-spacing: -0.06em;
  line-height: 0.92;
  color: var(--ink);
}

.wordmark--md {
  font-size: clamp(2.8rem, 10vw, 4.2rem);
}

.hero-line {
  margin: 18px 0 0;
  color: var(--muted);
  font-size: 15px;
  letter-spacing: 0.12em;
}

.tools {
  max-width: 420px;
  margin: 0 auto;
  padding: 8px 20px 48px;
}

.tool-card {
  width: 100%;
  text-align: left;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 22px 22px 20px;
  background: var(--surface-solid);
  box-shadow: var(--shadow);
  cursor: pointer;
  font: inherit;
  color: inherit;
}

.tool-card__title {
  display: block;
  font-size: 17px;
  font-weight: 600;
  margin-bottom: 6px;
}

.tool-card__desc {
  display: block;
  color: var(--muted);
  font-size: 13.5px;
}

.sheet {
  max-width: 720px;
  margin: 0 auto;
  padding: 22px 20px 48px;
}

.parse-row {
  display: flex;
  gap: 10px;
}

.field {
  flex: 1;
  min-width: 0;
  padding: 13px 16px;
  border-radius: 14px;
  border: 1px solid rgba(42, 40, 36, 0.12);
  background: var(--surface-solid);
  color: var(--ink);
  font: 15px/1.4 var(--font-ui);
  outline: none;
}

.btn {
  border: none;
  border-radius: 999px;
  padding: 0 18px;
  min-height: 46px;
  background: var(--accent);
  color: #fff;
  font: 500 14px/1 var(--font-ui);
  cursor: pointer;
  white-space: nowrap;
  transition: background 120ms ease, transform 100ms ease-out;
}

.btn:hover { background: var(--accent-hover); }
.btn:active:not(:disabled) { transform: scale(0.97); }
.btn:disabled { opacity: 0.5; cursor: default; }

.result-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin: 26px 0 14px;
}

.result-meta { min-width: 0; }

.result-title {
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.result-sub {
  color: var(--muted);
  font-size: 13px;
  margin-top: 2px;
}

.err {
  color: var(--danger);
  margin-top: 14px;
}

.img-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 12px;
}

.img-thumb {
  position: relative;
  border-radius: 16px;
  overflow: hidden;
  background: #ddd6cb;
  aspect-ratio: 3 / 4;
}

.img-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.img-save {
  position: absolute;
  right: 8px;
  bottom: 8px;
  border: none;
  background: rgba(42, 40, 36, 0.55);
  color: #fff;
  cursor: pointer;
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 13px;
  backdrop-filter: blur(8px);
}

.img-save:disabled { opacity: 0.6; cursor: default; }

.locked {
  max-width: 420px;
  margin: 0 auto;
  padding: 96px 24px 48px;
  text-align: center;
}

.locked-copy {
  margin: 22px auto 0;
  color: var(--muted);
  font-size: 16px;
  line-height: 1.7;
}

.boot {
  min-height: 100dvh;
  display: grid;
  place-items: center;
}

.boot .mark {
  font-size: 22px;
  opacity: 0.35;
}

@media (max-width: 520px) {
  .hero { padding-top: 56px; }
  .parse-row { flex-direction: column; }
  .btn { width: 100%; min-height: 44px; }
  .result-head { flex-direction: column; align-items: stretch; }
}

@media (prefers-reduced-transparency: reduce) {
  :root { --surface: #fffdf9; }
  .topbar { backdrop-filter: none; }
}

@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

- [ ] **Step 3: 构建校验 CSS/HTML 无语法错误**

Run: `cd frontend && npm run build`

Expected: 成功（页面内容尚未改完也可通过；若失败只修本任务引入的问题）

- [ ] **Step 4: Commit（仅当用户要求时）**

```bash
git add frontend/index.html frontend/src/theme.css
git commit -m "$(cat <<'EOF'
style: add paper theme tokens and site chrome

EOF
)"
```

---

### Task 3: 首页 + ToolCard

**Files:**
- Modify: `frontend/src/pages/Home.tsx`
- Modify: `frontend/src/components/ToolCard.tsx`

**Interfaces:**
- Consumes: `tool-card*`、`hero`、`wordmark`、`hero-line`、`tools`、`topbar`、`mark` 等类
- Produces: 首页视觉与试验场一致；副文案「cynic·百宝箱」

- [ ] **Step 1: 重写 `Home.tsx`**

```tsx
import ToolCard from "../components/ToolCard";

export default function Home() {
  return (
    <div className="paper-app">
      <header className="topbar topbar--ghost">
        <span className="mark mark--sm">nowm</span>
      </header>
      <section className="hero">
        <h1 className="wordmark">nowm</h1>
        <p className="hero-line">cynic·百宝箱</p>
      </section>
      <section className="tools">
        <ToolCard
          title="小红书无水印下载"
          desc="粘贴分享链接，解析并保存原图"
          to="/xhs"
        />
      </section>
    </div>
  );
}
```

- [ ] **Step 2: 重写 `ToolCard.tsx`**

保留 framer-motion 交互，去掉白底 inline 阴影，改用 `.tool-card`：

```tsx
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
```

- [ ] **Step 3: 本地目视**

Run: `cd frontend && npm run dev`

对照 `http://127.0.0.1:8765/` 试验场首页：大词标、副文案、单卡片、纸纹。

- [ ] **Step 4: Commit（仅当用户要求时）**

```bash
git add frontend/src/pages/Home.tsx frontend/src/components/ToolCard.tsx
git commit -m "$(cat <<'EOF'
feat: restyle home with nowm wordmark

EOF
)"
```

---

### Task 4: Locked + App 加载壳

**Files:**
- Modify: `frontend/src/pages/Locked.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `paper-app`、`locked`、`wordmark--md`、`boot`
- Produces: 未授权页与轻量 boot 态（避免白闪）

- [ ] **Step 1: 重写 `Locked.tsx`**

```tsx
export default function Locked() {
  return (
    <div className="paper-app">
      <header className="topbar topbar--ghost">
        <span className="mark mark--sm">nowm</span>
      </header>
      <section className="locked">
        <h1 className="wordmark wordmark--md">nowm</h1>
        <p className="locked-copy">
          需要邀请链接才能使用。
          <br />
          请向管理员索取专属链接后打开。
        </p>
      </section>
    </div>
  );
}
```

- [ ] **Step 2: 改 `App.tsx` 加载态**

将 `if (!ready) return null;` 改为：

```tsx
  if (!ready) {
    return (
      <div className="paper-app">
        <div className="boot">
          <span className="mark">nowm</span>
        </div>
      </div>
    );
  }
```

其余路由 / 鉴权逻辑保持不变。完整文件应为：

```tsx
import { useEffect, useState } from "react";
import { Routes, Route, useSearchParams } from "react-router-dom";
import Home from "./pages/Home";
import XhsTool from "./pages/XhsTool";
import Locked from "./pages/Locked";
import { claimInvite, fetchAuthStatus } from "./auth";

export default function App() {
  const [search, setSearch] = useSearchParams();
  const [ready, setReady] = useState(false);
  const [authed, setAuthed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const invite = search.get("invite");
      if (invite) {
        try {
          await claimInvite(invite);
        } catch {
          /* 无效邀请：稍后 status 仍为 false */
        }
        const next = new URLSearchParams(search);
        next.delete("invite");
        setSearch(next, { replace: true });
      }
      const ok = await fetchAuthStatus();
      if (!cancelled) {
        setAuthed(ok);
        setReady(true);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  if (!ready) {
    return (
      <div className="paper-app">
        <div className="boot">
          <span className="mark">nowm</span>
        </div>
      </div>
    );
  }
  if (!authed) return <Locked />;

  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/xhs" element={<XhsTool />} />
    </Routes>
  );
}
```

- [ ] **Step 3: `npm run build` 通过**

Run: `cd frontend && npm run build`

Expected: exit 0

- [ ] **Step 4: Commit（仅当用户要求时）**

```bash
git add frontend/src/pages/Locked.tsx frontend/src/App.tsx
git commit -m "$(cat <<'EOF'
feat: restyle locked screen and boot state

EOF
)"
```

---

### Task 5: 工具页 + ImageGrid

**Files:**
- Modify: `frontend/src/pages/XhsTool.tsx`
- Modify: `frontend/src/components/ImageGrid.tsx`

**Interfaces:**
- Consumes: `save.ts` 的 `saveAll` / `supportsFileShare`（签名不变）；`parseShare`（不变）
- Produces: 工具页纸感 UI；顶栏标题「小红书无水印」

- [ ] **Step 1: 重写 `XhsTool.tsx`**

逻辑与现文件相同，仅换类名与短标题：

```tsx
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
```

- [ ] **Step 2: 更新 `ImageGrid.tsx` 使用纸感类**

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
    <div className="img-grid">
      {images.map((im, i) => (
        <motion.div
          key={im.file_id}
          className="img-thumb"
          initial={reduced ? { opacity: 0 } : { opacity: 0, y: 12 }}
          animate={reduced ? { opacity: 1 } : { opacity: 1, y: 0 }}
          transition={{
            type: "spring",
            bounce: 0,
            duration: 0.4,
            delay: reduced ? 0 : i * 0.03,
          }}
        >
          <img src={im.url} loading="lazy" alt="" />
          <button
            type="button"
            className="img-save"
            onClick={() => onSave(im)}
            disabled={busy === im.file_id}
          >
            {busy === im.file_id ? "…" : shareLabel}
          </button>
        </motion.div>
      ))}
    </div>
  );
}
```

- [ ] **Step 3: 全量构建**

Run: `cd frontend && npm run build`

Expected: exit 0，无 TS 错误

- [ ] **Step 4: 手动验收清单**

1. 首页：大 `nowm`、副文案「cynic·百宝箱」、单卡片、纸纹可见  
2. 页面源码/UI 无「cynic 工具箱」  
3. 工具页短标题「小红书无水印」；解析 / 保存行为与改前一致  
4. 无 cookie 时 Locked 页居中词标 + 说明  
5. 首屏 auth 等待时有淡 `nowm`，非纯白闪  

- [ ] **Step 5: Commit（仅当用户要求时）**

```bash
git add frontend/src/pages/XhsTool.tsx frontend/src/components/ImageGrid.tsx
git commit -m "$(cat <<'EOF'
feat: restyle xhs tool page to paper UI

EOF
)"
```

---

### Task 6: README 品牌措辞（若有过时标题）

**Files:**
- Modify: `README.md`（仅当其中仍写「cynic 工具箱」作为产品名时）

**Interfaces:**
- Consumes: 无
- Produces: 文档中对外产品名与 UI 一致为 nowm

- [ ] **Step 1: 检索**

Run: `rg -n "cynic 工具箱|cynic工具箱" README.md docs frontend/src frontend/index.html || true`

- [ ] **Step 2: 若 README 标题仍是「cynic 工具箱」**

将用户可见产品名改为 `nowm`（可保留「作者/仓库归属 cynic」类说明）。**不要**改掉用户指定的首页副文案「cynic·百宝箱」。

- [ ] **Step 3: 最终构建**

Run: `cd frontend && npm run build`

Expected: exit 0

- [ ] **Step 4: Commit（仅当用户要求时）**

```bash
git add README.md
git commit -m "$(cat <<'EOF'
docs: align product name with nowm branding

EOF
)"
```

---

## Spec Coverage Checklist

| Spec 要求 | Task |
|-----------|------|
| 纸感颜色 token | Task 2 |
| Syne + Noto / 回退 | Task 2 |
| 纸纹 SVG | Task 1–2 |
| Favicon | Task 1–2 |
| 首页词标 + 副文案「cynic·百宝箱」 | Task 3 |
| 单工具卡 | Task 3 |
| Locked | Task 4 |
| 轻量加载态 | Task 4 |
| 工具页短标题与纸感控件 | Task 5 |
| 图格角标 | Task 5 |
| 不改 save/api/auth | 全文约束 |
| 无「cynic 工具箱」UI | Task 3–6 |
| reduced-motion / transparency | Task 2 |
| 验收对照试验场 | Task 3/5 |

## Placeholder / Consistency Self-Review

- 无 TBD；类名在 Task 2 定义，后续任务复用同一套。
- 副文案以当前 spec「cynic·百宝箱」为准（非试验场旧句「无水印，干净取图」）。
- Commit 步骤标注「仅当用户要求时」，符合仓库 git 习惯。
