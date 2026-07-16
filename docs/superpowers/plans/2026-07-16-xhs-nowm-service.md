# 小红书无水印下载服务 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把小红书无水印下载做成局域网自托管的前后端分离 Web 服务（cynic 工具箱），支持解析分享链接、展示图片、单张下载与一键打包 ZIP。

**Architecture:** FastAPI 后端提供解析/图片代理/打包三个 API 并托管 React 前端静态产物；因源站 CDN 有防盗链，图片统一由后端不带 Referer 代理拉取；单容器多阶段 Docker 部署，无数据库，日志文件做审计。

**Tech Stack:** Python 3.12 / FastAPI / httpx / pytest；React 18 + TypeScript + Vite + Motion（framer-motion）；Docker 多阶段（node:24-alpine + python:3.12-slim-bookworm）+ docker compose。

## Global Constraints

- 仓库根目录为 `nowm/`，所有路径以此为根；不引用外层 `media/` 等目录。
- CLI 脚本 `xhs_dl.py` 不纳入仓库。
- 无数据库；留痕仅用日志文件 `logs/access.log`（按天滚动，JSON 行）。
- 服务绑定 `0.0.0.0`，容器内端口 `8000`，宿主机默认 `8823`。
- 图片一律经后端代理拉取，后端请求 CDN 不带 `Referer`。
- 无水印图片 URL：`https://sns-img-qc.xhscdn.com/{file_id}?imageView2/format/png`，源站容灾域名顺序 `sns-img-qc / sns-img-bd / sns-img-hw / sns-img-qn`。
- 详情页请求需带浏览器 UA：`Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36`。
- 前端交互遵循 apple-design：按下即响应、弹簧动效默认 `bounce:0`、半透明材质、尊重 `prefers-reduced-motion`。

---

## File Structure

```
backend/
  app/
    __init__.py
    parser.py         # 链接提取、短链还原、详情页抓取、imageList 解析
    cdn.py            # 无水印 URL 拼接、多源站容灾拉取
    logging_conf.py   # 结构化审计日志
    main.py           # FastAPI app、路由、静态托管、异常处理
  tests/
    fixtures/sample_note.html
    test_parser.py
    test_cdn.py
    test_api.py
  requirements.txt
frontend/
  index.html
  package.json
  tsconfig.json
  vite.config.ts
  src/
    main.tsx
    App.tsx
    api.ts
    theme.css
    pages/Home.tsx
    pages/XhsTool.tsx
    components/ToolCard.tsx
    components/ImageGrid.tsx
    components/Pressable.tsx
Dockerfile
docker-compose.yml
```

---

## Task 1: 后端解析模块 parser.py

**Files:**
- Create: `backend/app/__init__.py`
- Create: `backend/app/parser.py`
- Create: `backend/tests/fixtures/sample_note.html`
- Create: `backend/tests/test_parser.py`
- Create: `backend/requirements.txt`

**Interfaces:**
- Produces:
  - `extract_link(text: str) -> str` — 从分享文案提取首个 xhslink/xiaohongshu 链接，找不到抛 `NoLinkError`。
  - `resolve(text: str, client: httpx.Client | None = None) -> str` — 提取链接；若为 xhslink 短链，跟随一次 302 返回 `Location`；否则原样返回。
  - `parse_note(html: str) -> NoteData` — 解析详情页 HTML，返回 `NoteData`；无 `__INITIAL_STATE__` 或图片为空抛 `ExpiredError`；结构异常抛 `ParseError`。
  - `@dataclass NoteData: note_id:str; title:str; author:str; images:list[ImageMeta]`
  - `@dataclass ImageMeta: file_id:str; width:int; height:int`
  - 异常类：`NoLinkError`, `ExpiredError`, `ParseError`（均继承 `XhsError(Exception)`）。

- [ ] **Step 1: 写 requirements.txt**

```
fastapi==0.115.6
uvicorn[standard]==0.34.0
httpx==0.28.1
pytest==8.3.4
```

- [ ] **Step 2: 写测试 fixture `backend/tests/fixtures/sample_note.html`**

```html
<!doctype html><html><head><title>t</title></head><body>
<script>
  window.__INITIAL_STATE__ = {"note":{"noteDetailMap":{"6a53ad2500000000060323d6":{"note":{
    "noteId":"6a53ad2500000000060323d6","type":"normal","title":"测试标题",
    "user":{"nickname":"测试作者","userId":"u1"},
    "desc":"描述",
    "imageList":[
      {"fileId":"notes_pre_post/aaa111","width":1440,"height":1920,"urlDefault":"http://sns-webpic-qc.xhscdn.com/x/aaa111!nd_dft_wlteh_jpg_3"},
      {"fileId":"notes_pre_post/bbb222","width":1080,"height":1440,"urlDefault":"http://sns-webpic-qc.xhscdn.com/x/bbb222!nd_dft_wlteh_jpg_3"}
    ]
  }}}}}
</script></body></html>
```

- [ ] **Step 3: 写失败测试 `backend/tests/test_parser.py`**

```python
import pathlib
import pytest
from app.parser import extract_link, parse_note, NoLinkError, ExpiredError, NoteData

FIX = pathlib.Path(__file__).parent / "fixtures" / "sample_note.html"

def test_extract_link_from_share_text():
    text = "标题党 http://xhslink.com/o/4bDk4vyM9uJ 存下这段话，去【小红书】"
    assert extract_link(text) == "http://xhslink.com/o/4bDk4vyM9uJ"

def test_extract_link_none_raises():
    with pytest.raises(NoLinkError):
        extract_link("没有链接的一段文字")

def test_parse_note_returns_images():
    note = parse_note(FIX.read_text(encoding="utf-8"))
    assert isinstance(note, NoteData)
    assert note.note_id == "6a53ad2500000000060323d6"
    assert note.title == "测试标题"
    assert note.author == "测试作者"
    assert [i.file_id for i in note.images] == ["notes_pre_post/aaa111", "notes_pre_post/bbb222"]
    assert note.images[0].width == 1440

def test_parse_note_empty_raises_expired():
    html = "<html><body>login wall no state</body></html>"
    with pytest.raises(ExpiredError):
        parse_note(html)
```

- [ ] **Step 4: 运行测试确认失败**

Run: `cd backend && python -m pytest tests/test_parser.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'app.parser'`）

- [ ] **Step 5: 实现 `backend/app/__init__.py`（空文件）与 `backend/app/parser.py`**

```python
# backend/app/__init__.py
```

```python
# backend/app/parser.py
import re
import json
from dataclasses import dataclass
import httpx

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

_LINK_RE = re.compile(r"https?://(?:xhslink\.com|www\.xiaohongshu\.com)/\S+")
_STATE_RE = re.compile(r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*</script>", re.S)


class XhsError(Exception):
    """基类"""


class NoLinkError(XhsError):
    pass


class ExpiredError(XhsError):
    pass


class ParseError(XhsError):
    pass


@dataclass
class ImageMeta:
    file_id: str
    width: int
    height: int


@dataclass
class NoteData:
    note_id: str
    title: str
    author: str
    images: list[ImageMeta]


def extract_link(text: str) -> str:
    m = _LINK_RE.search(text)
    if not m:
        raise NoLinkError("未识别到小红书链接")
    return m.group(0).rstrip("，,。）)]】")


def resolve(text: str, client: httpx.Client | None = None) -> str:
    url = extract_link(text)
    if "xhslink.com" not in url:
        return url
    own = client or httpx.Client(headers={"User-Agent": UA}, timeout=15,
                                 follow_redirects=False)
    try:
        r = own.get(url)
        loc = r.headers.get("location")
        if not loc:
            raise ParseError("短链未返回跳转地址")
        return loc
    finally:
        if client is None:
            own.close()


def parse_note(html: str) -> NoteData:
    m = _STATE_RE.search(html)
    if not m:
        raise ExpiredError("链接已失效，请重新复制分享链接")
    try:
        data = json.loads(m.group(1).replace("undefined", "null"))
        detail_map = data["note"]["noteDetailMap"]
        if not detail_map:
            raise ExpiredError("链接已失效，请重新复制分享链接")
        note = next(iter(detail_map.values()))["note"]
        images = [
            ImageMeta(file_id=i["fileId"], width=int(i.get("width", 0)),
                      height=int(i.get("height", 0)))
            for i in note.get("imageList", []) if i.get("fileId")
        ]
    except ExpiredError:
        raise
    except (KeyError, ValueError, TypeError, StopIteration) as e:
        raise ParseError(f"解析失败，接口可能已变更: {e}") from e
    if not images:
        raise ExpiredError("链接已失效，请重新复制分享链接")
    return NoteData(
        note_id=note.get("noteId", ""),
        title=note.get("title") or note.get("desc", "")[:20] or "小红书笔记",
        author=note.get("user", {}).get("nickname", ""),
        images=images,
    )
```

- [ ] **Step 6: 运行测试确认通过**

Run: `cd backend && python -m pytest tests/test_parser.py -v`
Expected: PASS（4 passed）

- [ ] **Step 7: Commit**

```bash
cd /path/to/nowm
git add backend/app/__init__.py backend/app/parser.py backend/requirements.txt backend/tests/
git commit -m "feat(backend): 添加小红书链接解析模块 parser"
```

---

## Task 2: CDN 拉取模块 cdn.py

**Files:**
- Create: `backend/app/cdn.py`
- Create: `backend/tests/test_cdn.py`

**Interfaces:**
- Consumes: 无（独立模块）。
- Produces:
  - `nowm_url(file_id: str, host: str = "sns-img-qc.xhscdn.com") -> str`
  - `fetch_image(file_id: str, client: httpx.Client | None = None, timeout: float = 15) -> bytes` — 依次尝试 `CDN_HOSTS`，不带 Referer；全部失败抛 `ImageFetchError`。
  - `CDN_HOSTS: list[str]`
  - 异常：`ImageFetchError(XhsError)`（从 `app.parser` 导入 `XhsError`）。

- [ ] **Step 1: 写失败测试 `backend/tests/test_cdn.py`**

```python
import pytest
import httpx
from app.cdn import nowm_url, fetch_image, ImageFetchError, CDN_HOSTS

def test_nowm_url_format():
    assert nowm_url("notes_pre_post/aaa") == \
        "https://sns-img-qc.xhscdn.com/notes_pre_post/aaa?imageView2/format/png"

def test_fetch_image_falls_back_on_error(monkeypatch):
    calls = []
    class FakeResp:
        def __init__(self, code, content=b""):
            self.status_code = code
            self.content = content
    class FakeClient:
        def get(self, url):
            calls.append(url)
            # 第一个 host 失败，第二个成功
            if CDN_HOSTS[0] in url:
                return FakeResp(403)
            return FakeResp(200, b"\x89PNG_data")
    data = fetch_image("notes_pre_post/aaa", client=FakeClient())
    assert data == b"\x89PNG_data"
    assert len(calls) == 2

def test_fetch_image_all_fail_raises(monkeypatch):
    class FakeResp:
        status_code = 403
        content = b""
    class FakeClient:
        def get(self, url):
            return FakeResp()
    with pytest.raises(ImageFetchError):
        fetch_image("notes_pre_post/aaa", client=FakeClient())
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && python -m pytest tests/test_cdn.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'app.cdn'`）

- [ ] **Step 3: 实现 `backend/app/cdn.py`**

```python
# backend/app/cdn.py
import httpx
from app.parser import XhsError, UA

CDN_HOSTS = [
    "sns-img-qc.xhscdn.com",
    "sns-img-bd.xhscdn.com",
    "sns-img-hw.xhscdn.com",
    "sns-img-qn.xhscdn.com",
]


class ImageFetchError(XhsError):
    pass


def nowm_url(file_id: str, host: str = "sns-img-qc.xhscdn.com") -> str:
    return f"https://{host}/{file_id}?imageView2/format/png"


def fetch_image(file_id: str, client: httpx.Client | None = None,
                timeout: float = 15) -> bytes:
    # 关键：不带 Referer，避免源站防盗链 403
    own = client or httpx.Client(headers={"User-Agent": UA}, timeout=timeout)
    try:
        for host in CDN_HOSTS:
            try:
                r = own.get(nowm_url(file_id, host))
            except httpx.HTTPError:
                continue
            if r.status_code == 200 and r.content:
                return r.content
        raise ImageFetchError(f"图片拉取失败: {file_id}")
    finally:
        if client is None:
            own.close()
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && python -m pytest tests/test_cdn.py -v`
Expected: PASS（3 passed）

- [ ] **Step 5: Commit**

```bash
git add backend/app/cdn.py backend/tests/test_cdn.py
git commit -m "feat(backend): 添加多源站容灾的图片拉取模块 cdn"
```

---

## Task 3: 日志与 FastAPI 应用 main.py

**Files:**
- Create: `backend/app/logging_conf.py`
- Create: `backend/app/main.py`
- Create: `backend/tests/test_api.py`

**Interfaces:**
- Consumes: `app.parser.{resolve, fetch_note_html?, parse_note, NoLinkError, ExpiredError, ParseError, UA}`；`app.cdn.{fetch_image, ImageFetchError}`。
  - 注：详情页抓取用内联 `httpx` 完成（见下），不新增 parser 导出。
- Produces:
  - `logging_conf.setup_logging() -> logging.Logger`
  - `logging_conf.log_event(logger, **fields) -> None`（写一行 JSON）
  - FastAPI `app`：`POST /api/parse`、`GET /api/image`、`POST /api/package`，并在生产模式挂载 `frontend/dist` 静态目录（目录不存在时跳过，方便本地开发）。

- [ ] **Step 1: 实现 `backend/app/logging_conf.py`**

```python
# backend/app/logging_conf.py
import json
import logging
import pathlib
import time
from logging.handlers import TimedRotatingFileHandler

LOG_DIR = pathlib.Path(__file__).resolve().parents[1] / "logs"


def setup_logging() -> logging.Logger:
    LOG_DIR.mkdir(exist_ok=True)
    logger = logging.getLogger("nowm")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    h = TimedRotatingFileHandler(LOG_DIR / "access.log", when="midnight",
                                 backupCount=30, encoding="utf-8")
    h.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(h)
    return logger


def log_event(logger: logging.Logger, **fields) -> None:
    fields.setdefault("timestamp", time.strftime("%Y-%m-%dT%H:%M:%S"))
    logger.info(json.dumps(fields, ensure_ascii=False))
```

- [ ] **Step 2: 写失败测试 `backend/tests/test_api.py`**

```python
import io
import zipfile
import pytest
from fastapi.testclient import TestClient
from app import main

@pytest.fixture
def client(monkeypatch):
    # 打桩：绕开真实网络
    from app import parser, cdn
    monkeypatch.setattr(main, "load_note", lambda share: parser.NoteData(
        note_id="n1", title="标题", author="作者",
        images=[parser.ImageMeta("notes_pre_post/aaa", 1440, 1920),
                parser.ImageMeta("notes_pre_post/bbb", 1080, 1440)]))
    monkeypatch.setattr(main, "fetch_image", lambda fid: b"\x89PNG" + fid.encode())
    return TestClient(main.app)

def test_parse_endpoint(client):
    r = client.post("/api/parse", json={"share": "http://xhslink.com/o/x"})
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "标题"
    assert len(body["images"]) == 2
    assert body["images"][0]["url"].startswith("/api/image?file_id=")

def test_image_endpoint(client):
    r = client.get("/api/image", params={"file_id": "notes_pre_post/aaa"})
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    assert r.content.startswith(b"\x89PNG")

def test_package_endpoint(client):
    r = client.post("/api/package",
                    json={"file_ids": ["notes_pre_post/aaa", "notes_pre_post/bbb"],
                          "title": "我的笔记"})
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/zip"
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    assert len(zf.namelist()) == 2
```

- [ ] **Step 3: 运行测试确认失败**

Run: `cd backend && python -m pytest tests/test_api.py -v`
Expected: FAIL（`ImportError`/`AttributeError: module 'app.main'`）

- [ ] **Step 4: 实现 `backend/app/main.py`**

```python
# backend/app/main.py
import io
import re
import time
import zipfile
import pathlib
import urllib.parse
import httpx
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import Response, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.parser import (resolve, parse_note, NoteData, UA,
                        NoLinkError, ExpiredError, ParseError)
from app.cdn import fetch_image, ImageFetchError
from app.logging_conf import setup_logging, log_event

logger = setup_logging()
app = FastAPI(title="nowm · cynic 工具箱")

FRONTEND_DIST = pathlib.Path(__file__).resolve().parents[2] / "frontend" / "dist"


class ParseIn(BaseModel):
    share: str


class PackageIn(BaseModel):
    file_ids: list[str]
    title: str = "xiaohongshu"


def load_note(share: str) -> NoteData:
    """解析分享文案 -> NoteData（含真实网络请求）"""
    with httpx.Client(headers={"User-Agent": UA}, timeout=15,
                      follow_redirects=False) as c:
        url = resolve(share, client=c)
        html = c.get(url, follow_redirects=True).text
    return parse_note(html)


def _safe_name(title: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', "_", title).strip() or "xiaohongshu"


@app.post("/api/parse")
def api_parse(body: ParseIn, request: Request):
    t0 = time.time()
    try:
        note = load_note(body.share)
    except NoLinkError as e:
        log_event(logger, client_ip=request.client.host, action="parse",
                  input=body.share, status="no_link")
        raise HTTPException(400, str(e))
    except ExpiredError as e:
        log_event(logger, client_ip=request.client.host, action="parse",
                  input=body.share, status="expired")
        raise HTTPException(422, str(e))
    except (ParseError, httpx.HTTPError) as e:
        log_event(logger, client_ip=request.client.host, action="parse",
                  input=body.share, status="parse_error")
        raise HTTPException(502, "解析失败，接口可能已变更")
    log_event(logger, client_ip=request.client.host, action="parse",
              input=body.share, note_id=note.note_id,
              image_count=len(note.images), status="ok",
              duration_ms=int((time.time() - t0) * 1000))
    return {
        "note_id": note.note_id,
        "title": note.title,
        "author": note.author,
        "images": [
            {"index": i, "file_id": im.file_id, "width": im.width,
             "height": im.height,
             "url": "/api/image?file_id=" + urllib.parse.quote(im.file_id, safe="")}
            for i, im in enumerate(note.images)
        ],
    }


@app.get("/api/image")
def api_image(request: Request, file_id: str = Query(...),
              download: int = 0):
    try:
        data = fetch_image(file_id)
    except ImageFetchError as e:
        raise HTTPException(502, str(e))
    log_event(logger, client_ip=request.client.host, action="image",
              file_id=file_id, status="ok", bytes=len(data))
    headers = {}
    if download:
        name = file_id.split("/")[-1] + ".png"
        headers["Content-Disposition"] = f'attachment; filename="{name}"'
    return Response(content=data, media_type="image/png", headers=headers)


@app.post("/api/package")
def api_package(body: PackageIn, request: Request):
    buf = io.BytesIO()
    ok = 0
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as zf:
        for idx, fid in enumerate(body.file_ids, 1):
            try:
                data = fetch_image(fid)
            except ImageFetchError:
                continue
            zf.writestr(f"{idx:02d}.png", data)
            ok += 1
    buf.seek(0)
    log_event(logger, client_ip=request.client.host, action="package",
              image_count=len(body.file_ids), ok=ok, status="ok")
    name = urllib.parse.quote(_safe_name(body.title) + ".zip")
    return StreamingResponse(
        buf, media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{name}"})


if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="static")
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd backend && python -m pytest tests/ -v`
Expected: PASS（全部通过）

- [ ] **Step 6: 手动冒烟（真实网络，可选）**

Run: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000`
然后另开终端：`curl -s -X POST localhost:8000/api/parse -H 'Content-Type: application/json' -d '{"share":"http://xhslink.com/o/4bDk4vyM9uJ"}' | head -c 400`
Expected: 返回含 `images` 的 JSON（若原链接已过期则返回 422，属正常）。

- [ ] **Step 7: Commit**

```bash
git add backend/app/logging_conf.py backend/app/main.py backend/tests/test_api.py
git commit -m "feat(backend): 添加 FastAPI 应用（解析/图片代理/打包）与审计日志"
```

---

## Task 4: 前端脚手架与工具箱首页

**Files:**
- Create: `frontend/package.json`, `frontend/tsconfig.json`, `frontend/vite.config.ts`, `frontend/index.html`
- Create: `frontend/src/main.tsx`, `frontend/src/App.tsx`, `frontend/src/theme.css`
- Create: `frontend/src/pages/Home.tsx`, `frontend/src/components/ToolCard.tsx`, `frontend/src/components/Pressable.tsx`

**Interfaces:**
- Produces:
  - `PressableProps { children; onClick?; className? }`，`<Pressable>` 按下 `scale(0.97)` 的通用可点组件。
  - `ToolCard` 组件：`{ title; desc; to }`，点击 `to` 路由跳转。
  - 路由：`/`（Home）、`/xhs`（工具页，Task 5 提供）。
  - Vite 开发代理：`/api` → `http://localhost:8000`。

- [ ] **Step 1: 写 `frontend/package.json`**

```json
{
  "name": "nowm-frontend",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.28.0",
    "framer-motion": "^11.15.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.12",
    "@types/react-dom": "^18.3.1",
    "@vitejs/plugin-react": "^4.3.4",
    "typescript": "^5.6.3",
    "vite": "^6.0.5"
  }
}
```

- [ ] **Step 2: 写 `frontend/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true
  },
  "include": ["src"]
}
```

- [ ] **Step 3: 写 `frontend/vite.config.ts`**

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: { "/api": "http://localhost:8000" },
  },
});
```

- [ ] **Step 4: 写 `frontend/index.html`**

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
    <title>cynic 工具箱</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 5: 写 `frontend/src/theme.css`**（Apple 风格基础：系统字体、材质、无障碍）

```css
:root {
  --bg: #f5f5f7;
  --surface: rgba(255, 255, 255, 0.72);
  --text: #1d1d1f;
  --muted: #6e6e73;
  --accent: #0071e3;
  --radius: 18px;
  font: 100%/1.5 -apple-system, BlinkMacSystemFont, "SF Pro Text",
        system-ui, "PingFang SC", "Microsoft YaHei", sans-serif;
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--bg); color: var(--text);
  -webkit-font-smoothing: antialiased;
}
.toolbar {
  position: sticky; top: 0; z-index: 10;
  background: var(--surface); backdrop-filter: saturate(180%) blur(20px);
  border-bottom: 1px solid rgba(0,0,0,0.06);
  padding: 14px 20px;
}
h1 { font-size: clamp(1.6rem, 4vw, 2.4rem); letter-spacing: -0.02em; line-height: 1.08; }
.container { max-width: 980px; margin: 0 auto; padding: 20px; }
.btn {
  border: none; border-radius: 980px; padding: 10px 18px;
  background: var(--accent); color: #fff; font-size: 15px; cursor: pointer;
}
.btn:disabled { opacity: 0.5; cursor: default; }
@media (prefers-reduced-transparency: reduce) {
  :root { --surface: #ffffff; }
  .toolbar { backdrop-filter: none; }
}
@media (prefers-reduced-motion: reduce) {
  * { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; }
}
```

- [ ] **Step 6: 写 `frontend/src/components/Pressable.tsx`**

```tsx
import { motion } from "framer-motion";
import type { ReactNode } from "react";

export default function Pressable(
  { children, onClick, className }:
  { children: ReactNode; onClick?: () => void; className?: string }
) {
  return (
    <motion.div
      className={className}
      onClick={onClick}
      whileTap={{ scale: 0.97 }}
      transition={{ type: "spring", bounce: 0, duration: 0.25 }}
      style={{ display: "inline-block", cursor: onClick ? "pointer" : "default" }}
    >
      {children}
    </motion.div>
  );
}
```

- [ ] **Step 7: 写 `frontend/src/components/ToolCard.tsx`**

```tsx
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
```

- [ ] **Step 8: 写 `frontend/src/pages/Home.tsx`**

```tsx
import ToolCard from "../components/ToolCard";

export default function Home() {
  return (
    <>
      <div className="toolbar"><h1>cynic 工具箱</h1></div>
      <div className="container">
        <div style={{ display: "grid", gridTemplateColumns:
          "repeat(auto-fill, minmax(260px, 1fr))", gap: 16 }}>
          <ToolCard title="小红书无水印下载"
                    desc="粘贴分享链接，解析并下载无水印原图"
                    to="/xhs" />
        </div>
      </div>
    </>
  );
}
```

- [ ] **Step 9: 写 `frontend/src/App.tsx` 与 `frontend/src/main.tsx`**

```tsx
// src/App.tsx
import { Routes, Route } from "react-router-dom";
import Home from "./pages/Home";
import XhsTool from "./pages/XhsTool";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/xhs" element={<XhsTool />} />
    </Routes>
  );
}
```

```tsx
// src/main.tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./theme.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);
```

> 注：`XhsTool` 在 Task 5 创建；本任务先建一个占位以便构建通过。

- [ ] **Step 10: 建 `XhsTool` 占位并安装依赖、构建验证**

创建 `frontend/src/pages/XhsTool.tsx` 占位：

```tsx
export default function XhsTool() {
  return <div className="container">工具页占位</div>;
}
```

Run: `cd frontend && npm install && npm run build`
Expected: 构建成功，生成 `frontend/dist/`。

- [ ] **Step 11: Commit**

```bash
git add frontend/package.json frontend/tsconfig.json frontend/vite.config.ts \
        frontend/index.html frontend/src/
git commit -m "feat(frontend): 搭建 Vite+React 脚手架与工具箱首页"
```

---

## Task 5: 小红书工具页（解析/展示/下载/打包）

**Files:**
- Create: `frontend/src/api.ts`
- Create: `frontend/src/components/ImageGrid.tsx`
- Modify: `frontend/src/pages/XhsTool.tsx`（替换占位）

**Interfaces:**
- Consumes: 后端 `POST /api/parse`、`GET /api/image?file_id=&download=1`、`POST /api/package`。
- Produces:
  - `api.ts`：`parseShare(share: string): Promise<NoteResp>`；`packageUrl(): string`（返回 `/api/package`）；类型 `NoteResp { note_id; title; author; images: ImageItem[] }`，`ImageItem { index; file_id; width; height; url }`。
  - `ImageGrid`：`{ images: ImageItem[] }`，每张图带单独下载按钮。

- [ ] **Step 1: 写 `frontend/src/api.ts`**

```ts
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
    body: JSON.stringify({ file_ids: fileIds, title }),
  });
  if (!r.ok) throw new Error("打包失败");
  const blob = await r.blob();
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `${title}.zip`;
  a.click();
  URL.revokeObjectURL(a.href);
}
```

- [ ] **Step 2: 写 `frontend/src/components/ImageGrid.tsx`**

```tsx
import { motion } from "framer-motion";
import type { ImageItem } from "../api";

export default function ImageGrid({ images }: { images: ImageItem[] }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns:
      "repeat(auto-fill, minmax(150px, 1fr))", gap: 12 }}>
      {images.map((im, i) => (
        <motion.div
          key={im.file_id}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ type: "spring", bounce: 0, duration: 0.4, delay: i * 0.03 }}
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
```

- [ ] **Step 3: 实现 `frontend/src/pages/XhsTool.tsx`**

```tsx
import { useState } from "react";
import { Link } from "react-router-dom";
import { parseShare, downloadZip, type NoteResp } from "../api";
import ImageGrid from "../components/ImageGrid";

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
              <button className="btn" onClick={onZip} disabled={zipping}>
                {zipping ? "打包中…" : "打包下载全部"}
              </button>
            </div>
            <ImageGrid images={note.images} />
          </div>
        )}
      </div>
    </>
  );
}
```

- [ ] **Step 4: 构建验证**

Run: `cd frontend && npm run build`
Expected: 构建成功，无 TS 错误。

- [ ] **Step 5: 端到端手动验证（后端已在 8000 运行）**

Run: `cd frontend && npm run dev` → 浏览器打开 `http://localhost:5173/xhs`，粘贴有效分享链接，确认：图片展示、单张「下载」、「打包下载全部」均正常。

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api.ts frontend/src/components/ImageGrid.tsx frontend/src/pages/XhsTool.tsx
git commit -m "feat(frontend): 实现小红书工具页（解析/展示/单张下载/打包）"
```

---

## Task 6: Docker 部署与文档收尾

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `.dockerignore`
- Modify: `README.md`（去掉"实现完成后"字样，补充实测启动说明）

**Interfaces:**
- Consumes: `backend/`、`frontend/` 全部产物。
- Produces: 可 `docker compose up -d --build` 启动的服务，监听宿主机 `8823`。

- [ ] **Step 1: 写 `.dockerignore`**

```
**/node_modules
**/dist
**/__pycache__
**/.venv
logs
.git
```

- [ ] **Step 2: 写多阶段 `Dockerfile`**

```dockerfile
# 阶段一：构建前端
FROM node:24-alpine AS frontend
WORKDIR /fe
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# 阶段二：后端运行时
FROM python:3.12-slim-bookworm
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY --from=frontend /fe/dist ./frontend/dist
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

> 注：`main.py` 中 `FRONTEND_DIST` 为 `parents[2]/frontend/dist`。容器内 `app/main.py` 的 `parents[2]` 为 `/`，需保证结构一致。实现时将 `FRONTEND_DIST` 改为读取环境变量 `FRONTEND_DIST`（默认 `./frontend/dist` 相对工作目录），并在 compose/CMD 的工作目录 `/app` 下放置 `frontend/dist`。对应修改 `main.py`：

```python
import os
FRONTEND_DIST = pathlib.Path(os.environ.get("FRONTEND_DIST", "frontend/dist"))
```

- [ ] **Step 3: 写 `docker-compose.yml`**

```yaml
services:
  nowm:
    build: .
    image: nowm:latest
    container_name: nowm
    ports:
      - "8823:8000"
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
```

- [ ] **Step 4: 修正 main.py 的 FRONTEND_DIST（配合 Docker 工作目录）**

在 `backend/app/main.py` 中把：

```python
FRONTEND_DIST = pathlib.Path(__file__).resolve().parents[2] / "frontend" / "dist"
```

改为：

```python
import os
FRONTEND_DIST = pathlib.Path(
    os.environ.get("FRONTEND_DIST",
                   str(pathlib.Path(__file__).resolve().parents[2] / "frontend" / "dist")))
```

本地开发时 `parents[2]` 指向仓库根的 `frontend/dist`；容器内设 `FRONTEND_DIST=frontend/dist`（工作目录 `/app`）。在 Dockerfile 的 CMD 前加：`ENV FRONTEND_DIST=frontend/dist`。

- [ ] **Step 5: 构建并启动验证**

Run: `docker compose up -d --build`
Run: `curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8823/`
Expected: `200`（返回前端页面）。
Run: `docker compose logs --tail 20`
Expected: uvicorn 启动无报错。

- [ ] **Step 6: 更新 `README.md`**

去掉"实现完成后""将在实现阶段补齐"等字样，"快速开始"改为实测可用的：

```bash
docker compose up -d --build
# 浏览器访问 http://<服务器IP>:8823
```

- [ ] **Step 7: Commit**

```bash
git add Dockerfile docker-compose.yml .dockerignore backend/app/main.py README.md
git commit -m "feat: 添加 Docker 多阶段构建与 compose 部署，收尾文档"
```

---

## Self-Review

**1. Spec coverage:**
- 局域网访问/绑定 0.0.0.0 → Task 6 compose `8823:8000` + uvicorn `--host 0.0.0.0` ✓
- 无 DB、日志审计 → Task 3 `logging_conf` + 各接口 `log_event` ✓
- 单容器多阶段 Docker → Task 6 ✓
- POST /api/parse、GET /api/image、POST /api/package → Task 3 ✓
- 图片经后端代理、无 Referer、多源站容灾 → Task 2 `cdn.fetch_image` ✓
- 错误处理（无链接 400 / 过期 422 / 解析失败 502 / 单图容灾）→ Task 3 + Task 2 ✓
- 工具箱首页 + 工具页 → Task 4 + Task 5 ✓
- 输入框 + 解析按钮 + 图片展示 + 单张下载 + 打包下载 → Task 5 ✓
- Apple 风格（按下响应、弹簧、材质、无障碍）→ Task 4 theme.css/Pressable + Task 5 动效 ✓

**2. Placeholder scan:** Task 4 含 `XhsTool` 占位，但明确在 Task 5 替换为完整实现，非遗留占位；其余步骤均含完整代码。

**3. Type consistency:**
- `NoteData(note_id, title, author, images)` / `ImageMeta(file_id, width, height)` 在 Task 1 定义，Task 3 一致使用。
- `fetch_image(file_id, client=, timeout=)` Task 2 定义，Task 3 以 `fetch_image(fid)` 调用一致。
- 前端 `ImageItem/NoteResp` Task 5 `api.ts` 定义，`ImageGrid`/`XhsTool` 一致使用。
- `load_note`、`fetch_image` 在 Task 3 测试中被 monkeypatch，main.py 中均为模块级可打桩符号 ✓。
