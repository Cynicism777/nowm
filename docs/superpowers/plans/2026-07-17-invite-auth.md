# 共享邀请链接鉴权 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用共享邀请链接换长期 Session Cookie，未授权者无法使用业务 API，授权者约 60 天内无需重复操作。

**Architecture:** 后端新增无状态 HMAC Cookie 会话模块 + FastAPI 中间件保护业务 API；前端启动时处理 `?invite=` 并做登录门闸。配置经环境变量注入，缺配置则拒绝启动。

**Tech Stack:** FastAPI / Starlette middleware；Python `hmac`+`hashlib`；React 门闸组件；Docker Compose `env_file`。

## Global Constraints

- 规格依据：`docs/superpowers/specs/2026-07-17-invite-auth-design.md`。
- 仓库根目录为 `nowm/`；路径以此为根。
- 无数据库；Cookie 名必须为 `nowm_session`；载荷格式 `v1.<exp_unix>.<hmac_hex>`。
- 邀请校验必须用恒定时间比较（对 SHA-256 摘要做 `hmac.compare_digest`，避免长度不等抛错）。
- 未配置 `INVITE_TOKEN` 或 `SESSION_SECRET` 时进程拒绝启动（lifespan 校验）。
- 业务 API（`/api/parse`、`/api/image`、`/api/package`）无有效 Cookie → `401`；`/api/auth/claim`、`/api/auth/status` 放行。
- 前端无单测框架；后端用 pytest + TestClient；前端「构建 + 手动端到端」。
- 提交信息不写 `Co-authored-by`。

---

## File Structure

```
backend/app/auth.py              # 新增：配置、签发/校验 session、invite 比较
backend/app/main.py              # 改：lifespan、claim/status、鉴权中间件
backend/tests/conftest.py        # 新增：测试环境变量默认值
backend/tests/test_auth.py       # 新增：鉴权用例
backend/tests/test_api.py        # 改：业务 API 用例先 claim
frontend/src/auth.ts             # 新增：claimInvite / fetchAuthStatus
frontend/src/pages/Locked.tsx    # 新增：需要邀请说明页
frontend/src/App.tsx             # 改：启动门闸
frontend/src/api.ts              # 改：fetch 加 credentials:"include"（保险）
docker-compose.yml               # 改：env_file: .env
.gitignore                       # 改：忽略 .env
.env.example                     # 新增：变量模板（无真实密钥）
README.md                        # 改：邀请链接 / 生成密钥 / 吊销说明
```

---

### Task 1: 后端会话模块 `auth.py`（TDD）

**Files:**
- Create: `backend/app/auth.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_auth_unit.py`

**Interfaces:**
- Produces:
  - `COOKIE_NAME = "nowm_session"`
  - `class AuthConfig`: `invite_token: str`, `session_secret: str`, `session_days: int`, `cookie_secure: bool`
  - `load_config() -> AuthConfig`（缺必填变量则 `RuntimeError`）
  - `invite_ok(provided: str, expected: str) -> bool`
  - `mint_session(secret: str, days: int, *, now: int | None = None) -> str`
  - `verify_session(value: str, secret: str, *, now: int | None = None) -> bool`
  - `session_cookie_kwargs(cfg: AuthConfig) -> dict`（供 `Response.set_cookie`）

- [ ] **Step 1: 写失败单测 `backend/tests/test_auth_unit.py`**

```python
import time
import pytest
from app import auth


def test_invite_ok_accepts_match():
    assert auth.invite_ok("abc", "abc") is True
    assert auth.invite_ok("abc", "abd") is False
    assert auth.invite_ok("", "abd") is False


def test_mint_and_verify_roundtrip():
    secret = "test-secret-please-change"
    token = auth.mint_session(secret, days=60, now=1_700_000_000)
    assert auth.verify_session(token, secret, now=1_700_000_000) is True
    assert auth.verify_session(token, secret, now=1_700_000_000 + 60 * 86400 + 1) is False
    assert auth.verify_session(token, "other-secret", now=1_700_000_000) is False
    assert auth.verify_session("v1.1.deadbeef", secret, now=1_700_000_000) is False
    assert auth.verify_session("garbage", secret, now=1_700_000_000) is False


def test_load_config_requires_env(monkeypatch):
    monkeypatch.delenv("INVITE_TOKEN", raising=False)
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    with pytest.raises(RuntimeError):
        auth.load_config()
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && python -m pytest tests/test_auth_unit.py -v`
Expected: FAIL（`app.auth` 不存在或符号缺失）

- [ ] **Step 3: 实现 `backend/app/auth.py`**

```python
from __future__ import annotations

import hashlib
import hmac
import os
import time
from dataclasses import dataclass

COOKIE_NAME = "nowm_session"


@dataclass(frozen=True)
class AuthConfig:
    invite_token: str
    session_secret: str
    session_days: int = 60
    cookie_secure: bool = True


def load_config() -> AuthConfig:
    invite = os.environ.get("INVITE_TOKEN", "").strip()
    secret = os.environ.get("SESSION_SECRET", "").strip()
    if not invite or not secret:
        raise RuntimeError("INVITE_TOKEN and SESSION_SECRET are required")
    days = int(os.environ.get("SESSION_DAYS", "60"))
    secure = os.environ.get("COOKIE_SECURE", "true").strip().lower() in (
        "1", "true", "yes", "on",
    )
    return AuthConfig(
        invite_token=invite,
        session_secret=secret,
        session_days=days,
        cookie_secure=secure,
    )


def invite_ok(provided: str, expected: str) -> bool:
    a = hashlib.sha256(provided.encode("utf-8")).digest()
    b = hashlib.sha256(expected.encode("utf-8")).digest()
    return hmac.compare_digest(a, b)


def mint_session(secret: str, days: int, *, now: int | None = None) -> str:
    ts = int(now if now is not None else time.time())
    exp = ts + days * 86400
    msg = f"v1.{exp}"
    sig = hmac.new(secret.encode("utf-8"), msg.encode("utf-8"),
                   hashlib.sha256).hexdigest()
    return f"{msg}.{sig}"


def verify_session(value: str, secret: str, *, now: int | None = None) -> bool:
    parts = value.split(".")
    if len(parts) != 3 or parts[0] != "v1":
        return False
    _, exp_s, sig = parts
    try:
        exp = int(exp_s)
    except ValueError:
        return False
    msg = f"v1.{exp}"
    expect = hmac.new(secret.encode("utf-8"), msg.encode("utf-8"),
                      hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expect):
        return False
    ts = int(now if now is not None else time.time())
    return ts <= exp


def session_cookie_kwargs(cfg: AuthConfig) -> dict:
    return {
        "key": COOKIE_NAME,
        "httponly": True,
        "path": "/",
        "samesite": "lax",
        "secure": cfg.cookie_secure,
        "max_age": cfg.session_days * 86400,
    }
```

- [ ] **Step 4: 跑单测确认通过**

Run: `cd backend && python -m pytest tests/test_auth_unit.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/auth.py backend/tests/test_auth_unit.py
git commit -m "feat: add invite session HMAC helpers"
```

---

### Task 2: 接入 main.py（claim / status / 中间件 / lifespan）

**Files:**
- Modify: `backend/app/main.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_auth.py`
- Modify: `backend/tests/test_api.py`

**Interfaces:**
- Consumes: Task 1 的 `load_config`、`invite_ok`、`mint_session`、`verify_session`、`session_cookie_kwargs`、`COOKIE_NAME`
- Produces:
  - `GET /api/auth/claim?invite=` → `{ok: true}` + Set-Cookie / `401`
  - `GET /api/auth/status` → `{authenticated: bool}`
  - 中间件保护以 `/api/` 开头且路径不属于 `/api/auth/` 的请求

- [ ] **Step 1: 添加 `backend/tests/conftest.py`（在导入 app 前设环境变量）**

```python
import os

os.environ.setdefault("INVITE_TOKEN", "test-invite-token-xxxxxxxxxxxxxxxx")
os.environ.setdefault("SESSION_SECRET", "test-session-secret-xxxxxxxxxxxxxx")
os.environ.setdefault("COOKIE_SECURE", "false")
os.environ.setdefault("SESSION_DAYS", "60")
```

- [ ] **Step 2: 写 `backend/tests/test_auth.py`（先失败）**

```python
import pytest
from fastapi.testclient import TestClient
from app import main, auth


@pytest.fixture
def client(monkeypatch):
    from app import parser
    monkeypatch.setattr(main, "load_note", lambda share: parser.NoteData(
        note_id="n1", title="标题", author="作者",
        images=[parser.ImageMeta("notes_pre_post/aaa", 1440, 1920)]))
    monkeypatch.setattr(main, "fetch_image", lambda fid: b"\x89PNG" + fid.encode())
    return TestClient(main.app)


def test_status_unauthenticated(client):
    r = client.get("/api/auth/status")
    assert r.status_code == 200
    assert r.json() == {"authenticated": False}


def test_claim_bad_invite(client):
    r = client.get("/api/auth/claim", params={"invite": "wrong"})
    assert r.status_code == 401
    assert auth.COOKIE_NAME not in r.cookies


def test_claim_and_status(client):
    r = client.get("/api/auth/claim",
                   params={"invite": "test-invite-token-xxxxxxxxxxxxxxxx"})
    assert r.status_code == 200
    assert r.json() == {"ok": True}
    assert auth.COOKIE_NAME in r.cookies
    s = client.get("/api/auth/status")
    assert s.json() == {"authenticated": True}


def test_parse_requires_auth(client):
    r = client.post("/api/parse", json={"share": "http://xhslink.com/o/x"})
    assert r.status_code == 401


def test_parse_ok_after_claim(client):
    client.get("/api/auth/claim",
               params={"invite": "test-invite-token-xxxxxxxxxxxxxxxx"})
    r = client.post("/api/parse", json={"share": "http://xhslink.com/o/x"})
    assert r.status_code == 200
```

- [ ] **Step 3: 跑测确认 claim/中间件相关失败**

Run: `cd backend && python -m pytest tests/test_auth.py -v`
Expected: FAIL（路由/中间件尚未实现）

- [ ] **Step 4: 修改 `backend/app/main.py`**

在文件顶部 imports 中增加：

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, Query, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app import auth as authlib
```

将 `app = FastAPI(...)` 替换为带 lifespan 的版本，并在创建 app 后立刻挂中间件与 auth 路由（业务路由保持原样；SPA fallback 仍在文件末尾）。

关键片段（插入/替换位置按现有 `main.py` 结构）：

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.auth_cfg = authlib.load_config()
    yield


app = FastAPI(title="nowm · cynic 工具箱", lifespan=lifespan)


class SessionAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path.startswith("/api/") and not path.startswith("/api/auth/"):
            cfg = request.app.state.auth_cfg
            raw = request.cookies.get(authlib.COOKIE_NAME, "")
            if not authlib.verify_session(raw, cfg.session_secret):
                return Response(
                    content='{"detail":"Unauthorized"}',
                    status_code=401,
                    media_type="application/json",
                )
        return await call_next(request)


app.add_middleware(SessionAuthMiddleware)


@app.get("/api/auth/claim")
def api_auth_claim(invite: str = Query(...)):
    cfg = app.state.auth_cfg
    if not authlib.invite_ok(invite, cfg.invite_token):
        raise HTTPException(401, "邀请无效")
    value = authlib.mint_session(cfg.session_secret, cfg.session_days)
    resp = Response(
        content='{"ok":true}',
        media_type="application/json",
    )
    kw = authlib.session_cookie_kwargs(cfg)
    resp.set_cookie(value=value, **kw)
    return resp


@app.get("/api/auth/status")
def api_auth_status(request: Request):
    cfg = app.state.auth_cfg
    raw = request.cookies.get(authlib.COOKIE_NAME, "")
    ok = authlib.verify_session(raw, cfg.session_secret)
    return {"authenticated": ok}
```

注意：`TestClient` 会触发 lifespan，故 `app.state.auth_cfg` 在测试中可用。若本地直接 `import main` 后未启动 lifespan，中间件需容忍——以 lifespan 为准即可。

- [ ] **Step 5: 更新 `backend/tests/test_api.py` 的 client fixture，先 claim**

在 `client` fixture 里 `return TestClient(...)` 之前或之后：

```python
    c = TestClient(main.app)
    c.get("/api/auth/claim",
          params={"invite": "test-invite-token-xxxxxxxxxxxxxxxx"})
    return c
```

（fixture 开头保留原有 monkeypatch。）

- [ ] **Step 6: 跑全部后端测试**

Run: `cd backend && python -m pytest -v`
Expected: 全部 PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/main.py backend/tests/conftest.py backend/tests/test_auth.py backend/tests/test_api.py
git commit -m "feat: protect APIs with invite session cookie"
```

---

### Task 3: 前端门闸与 claim

**Files:**
- Create: `frontend/src/auth.ts`
- Create: `frontend/src/pages/Locked.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/api.ts`

**Interfaces:**
- Consumes: `/api/auth/claim`、`/api/auth/status`
- Produces:
  - `claimInvite(invite: string): Promise<void>`
  - `fetchAuthStatus(): Promise<boolean>`
  - `Locked` 页面组件
  - `App` 在未登录时只渲染 `Locked`

- [ ] **Step 1: 写 `frontend/src/auth.ts`**

```ts
export async function claimInvite(invite: string): Promise<void> {
  const r = await fetch(
    `/api/auth/claim?invite=${encodeURIComponent(invite)}`,
    { credentials: "include" },
  );
  if (!r.ok) throw new Error("邀请无效");
}

export async function fetchAuthStatus(): Promise<boolean> {
  const r = await fetch("/api/auth/status", { credentials: "include" });
  if (!r.ok) return false;
  const body = await r.json();
  return !!body.authenticated;
}
```

- [ ] **Step 2: 写 `frontend/src/pages/Locked.tsx`**

```tsx
export default function Locked() {
  return (
    <>
      <div className="toolbar"><h1>cynic 工具箱</h1></div>
      <div className="container" style={{ paddingTop: 48 }}>
        <p style={{ color: "var(--muted)", fontSize: 17, maxWidth: 420 }}>
          需要邀请链接才能使用。请向管理员索取专属链接后打开。
        </p>
      </div>
    </>
  );
}
```

- [ ] **Step 3: 改 `frontend/src/App.tsx`**

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

  if (!ready) return null;
  if (!authed) return <Locked />;

  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/xhs" element={<XhsTool />} />
    </Routes>
  );
}
```

说明：`useSearchParams` 要求在 `BrowserRouter` 内；当前 `main.tsx` 已包裹，OK。`useEffect` 依赖刻意留空（只跑一次启动逻辑）；eslint 若抱怨可加注释禁用该行。

- [ ] **Step 4: 改 `frontend/src/api.ts` 所有 `fetch` 增加 `credentials: "include"`**

`parseShare`：

```ts
  const r = await fetch("/api/parse", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ share }),
  });
```

`downloadZip` 同样加上 `credentials: "include"`。

- [ ] **Step 5: 构建前端**

Run: `cd frontend && npm run build`
Expected: 成功，无 TypeScript 错误

- [ ] **Step 6: Commit**

```bash
git add frontend/src/auth.ts frontend/src/pages/Locked.tsx frontend/src/App.tsx frontend/src/api.ts
git commit -m "feat: frontend invite gate and claim flow"
```

---

### Task 4: 部署配置与文档

**Files:**
- Modify: `docker-compose.yml`
- Modify: `.gitignore`
- Create: `.env.example`
- Modify: `README.md`

- [ ] **Step 1: 改 `docker-compose.yml`**

```yaml
services:
  nowm:
    build: .
    image: nowm:latest
    container_name: nowm
    ports:
      - "8823:8000"
    env_file:
      - .env
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
```

- [ ] **Step 2: `.gitignore` 追加**

```
.env
```

- [ ] **Step 3: 写 `.env.example`**

```
INVITE_TOKEN=
SESSION_SECRET=
SESSION_DAYS=60
COOKIE_SECURE=true
```

- [ ] **Step 4: 在 `README.md`「快速开始」之后增加章节「访问控制（邀请链接）」**

内容须包含：

1. 复制 `.env.example` 为 `.env`
2. 生成：`openssl rand -hex 32`（分别填 `INVITE_TOKEN` 与 `SESSION_SECRET`）
3. 邀请 URL：`https://<你的域名>/?invite=<INVITE_TOKEN>`（局域网调试可用 `http://<IP>:8823/?invite=...`，此时 `.env` 设 `COOKIE_SECURE=false`）
4. 吊销：换 `INVITE_TOKEN` 使旧链接失效；换 `SESSION_SECRET` 使全部 Cookie 立即失效，然后 `docker compose up -d`

- [ ] **Step 5: 本地生成 `.env`（不提交）并重建验证**

```bash
cp .env.example .env
# 写入真实随机值；局域网验证可设 COOKIE_SECURE=false
docker compose up -d --build
```

验证命令（把 `TOKEN` 换成 `.env` 里的值）：

```bash
# 无 cookie → 401
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://127.0.0.1:8823/api/parse \
  -H 'Content-Type: application/json' -d '{"share":"x"}'
# Expected: 401

# claim → 200，再 parse
curl -s -c /tmp/nowm.ck -b /tmp/nowm.ck \
  "http://127.0.0.1:8823/api/auth/claim?invite=TOKEN"
# Expected: {"ok":true}

curl -s -o /dev/null -w "%{http_code}\n" -c /tmp/nowm.ck -b /tmp/nowm.ck \
  -X POST http://127.0.0.1:8823/api/parse \
  -H 'Content-Type: application/json' -d '{"share":"x"}'
# Expected: 400 或 502 等业务码，绝不是 401（说明已过鉴权）
```

浏览器：无 invite 打开首页应见 Locked；带正确 `?invite=` 应进入工具箱，刷新后仍可用。

- [ ] **Step 6: Commit（不含 `.env`）**

```bash
git add docker-compose.yml .gitignore .env.example README.md
git commit -m "chore: wire invite auth env and document access control"
```

---

## Spec Coverage Checklist

| Spec 项 | Task |
|---------|------|
| 共享 invite + HMAC Cookie | 1–2 |
| claim / status API | 2 |
| 业务 API 401 | 2 |
| 缺配置拒绝启动 | 2（lifespan + `load_config`） |
| 前端门闸 + 清 URL | 3 |
| compose / `.env` / README / 吊销 | 4 |
| 测试要点 §8 | 1–2 + Task 4 curl |

## Placeholder / Consistency Self-Review

- Cookie 名全程 `nowm_session`；载荷 `v1.<exp>.<sig>` 与 `auth.py` 一致。
- 测试 invite 字面量与 `conftest.py` / `test_auth.py` / `test_api.py` 一致：`test-invite-token-xxxxxxxxxxxxxxxx`。
- 无 TBD/TODO 占位。
