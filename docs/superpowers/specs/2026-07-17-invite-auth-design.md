# 共享邀请链接鉴权 — 设计文档

- 日期：2026-07-17
- 项目：nowm（cynic 工具箱）
- 关联：`2026-07-16-xhs-nowm-service-design.md`、`2026-07-17-adaptive-save-design.md`

## 1. 背景与问题

服务原按局域网个人工具箱设计，**无鉴权**。现已经网关暴露到公网，陌生人可直接调用
`/api/parse`、`/api/image`、`/api/package`，存在滥用与刷流量风险。

需求：

- 只允许有授权的人使用（本人 + 少数熟人，**共用同一授权**）
- 鉴权做在 **nowm 应用内**（不依赖网关 Access / Basic Auth）
- **不想每次输入密钥**：首次用邀请链接换长期会话后，同一浏览器约 60 天内免操作
- 保持单容器、无数据库

## 2. 目标与约束

- 持有有效邀请链接的人：打开一次即可获得 Session Cookie，之后直接使用工具箱
- 无 Cookie 且无有效 invite：看不到可用工具 UI，业务 API 一律 `401`
- 吊销：换环境变量即可（见 §6），无需改代码
- YAGNI：不多用户、不一事一链、无管理后台、无口令登录页、无 IP 白名单

## 3. 方案选择

已否决：网关层鉴权（用户明确要应用内）；共享口令表单（用户选邀请链接）；HTTP Basic Auth（体验差）。

采用：**长期有效的共享邀请 token**（非一次性）+ **HMAC 签名 Session Cookie**。

## 4. 架构

```
浏览器
  │  首次：https://host/?invite=<INVITE_TOKEN>
  ▼
前端：检测 query → fetch /api/auth/claim（credentials: include）→ replaceState 清 invite
  │
后端 claim：恒定时间比较 invite → Set-Cookie(nowm_session) → 200 JSON
  │
之后请求：Cookie 自动带上
  ▼
中间件：验签 + 未过期 → 放行 /api/parse|image|package
         否则 → 401
```

静态资源（HTML/JS/CSS）仍可匿名下载；**敏感能力全部在业务 API**，由 Cookie 守门。

## 5. 接口与 Cookie

### 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `INVITE_TOKEN` | 是 | 共享邀请串，建议 ≥32 字节密码学随机 |
| `SESSION_SECRET` | 是 | 签发 Cookie 的 HMAC 密钥 |
| `SESSION_DAYS` | 否 | 默认 `60` |
| `COOKIE_SECURE` | 否 | 默认 `true`；仅本地 HTTP 调试可设 `false` |

未配置 `INVITE_TOKEN` 或 `SESSION_SECRET`：**uvicorn 进程拒绝启动**（启动期校验并退出），避免公网裸奔。

### API

| 方法 | 路径 | 鉴权 | 行为 |
|------|------|------|------|
| GET | `/api/auth/claim?invite=` | 无 | 用 `hmac.compare_digest` 与 `INVITE_TOKEN` 比较；通过则下发 Cookie，返回 `{ok:true}`；失败 `401` |
| GET | `/api/auth/status` | 无 | `{authenticated: bool}`，供前端门闸 |
| POST/GET | `/api/parse`、`/api/image`、`/api/package` | 需有效 Cookie | 行为不变；无/无效 Cookie → `401` |

Cookie 名：`nowm_session`。属性：`HttpOnly; Path=/; SameSite=Lax; Max-Age=SESSION_DAYS*86400`；`Secure` 由 `COOKIE_SECURE` 控制（生产默认开）。

Cookie 值：无状态签名载荷 `v1.<exp_unix>.<hmac>`（HMAC-SHA256，密钥=`SESSION_SECRET`，消息为 `v1.<exp_unix>`）。服务端只验签与过期，不落库。

前端打开带 `?invite=` 的 URL 时用 `fetch(..., {credentials:"include"})` 调 claim；成功后 `history.replaceState` 去掉 query，避免 token 留在地址栏与历史记录。claim 走 JSON+Set-Cookie，**不使用 302**（便于 SPA 控制清 URL）。

### 前端门闸

- 启动：若 URL 有 `invite` → claim；再调 `/api/auth/status`
- `authenticated` → 正常渲染现有路由
- 否则 → 全屏「需要邀请链接」说明页（极简，保持现有视觉语言），不渲染工具页

## 6. 吊销与安全边界

| 操作 | 效果 |
|------|------|
| 更换 `INVITE_TOKEN` | 旧邀请 URL 失效；**已持有 Cookie 者仍可用到过期** |
| 更换 `SESSION_SECRET` | **全部已发 Cookie 立即失效**（紧急止血） |

**防住**：无邀请者调用业务 API。
**防不住**：邀请链接被转发/泄露；他人使用已登录浏览器。
缓解：链接仅私发；泄露先换 token，紧急再换 secret。

## 7. 部署改动

- `docker-compose.yml`：通过 `env_file: .env`（或 `environment`）注入上述变量
- 根目录 `.gitignore` 增加 `.env`（当前仓库尚未忽略，实现时补上）
- `README.md`：用 `openssl rand -hex 32` 生成 token/secret 的示例、邀请 URL 格式（`https://<host>/?invite=<INVITE_TOKEN>`）、吊销步骤
- 依赖现有网关 HTTPS + uvicorn `--proxy-headers`，以便 `Secure` Cookie 在反代后可用

## 8. 测试要点

- 无 Cookie 调 `/api/parse` → `401`
- 正确 `invite` claim → 有 Cookie；随后业务 API 可通
- 错误 `invite` → `401`，不下发 Cookie
- 过期或篡改 Cookie → `401`
- 更换 `SESSION_SECRET` 后旧 Cookie → `401`
- `/api/auth/status` 在登录前后分别返回 false/true

## 9. 成功标准

- 陌生人直接打开站点只能看到「需要邀请」页，无法解析/下图
- 持邀请链接打开一次后，约 60 天内同浏览器无需再带 invite
- 换 secret 可立即踢掉全部会话；全程无数据库
