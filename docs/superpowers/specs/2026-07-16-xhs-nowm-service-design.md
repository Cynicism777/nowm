# 小红书无水印下载服务 — 设计文档

- 日期：2026-07-16
- 项目：nowm（cynic 工具箱）
- 仓库：github.com:Cynicism777/nowm.git

## 1. 目标

把已跑通的命令行脚本 `xhs_dl.py` 升级为一个前后端分离的 Web 服务，部署在服务器上供局域网随时随地使用。网页定位为「cynic 工具箱」，当前收录一个工具：小红书无水印图片下载。

核心能力：粘贴小红书分享链接 → 解析 → 展示笔记全部图片 → 单张下载 / 一键打包下载，全部无水印原图。

## 2. 范围与约束

- **访问方式**：局域网（服务绑定 `0.0.0.0`，同网段手机/电脑均可访问），不做登录鉴权、不做 HTTPS。
- **无数据库**：无状态服务，仅通过日志文件做留痕/审计。
- **部署**：Docker + docker compose，单容器多阶段构建，稳定长期运行。
- **YAGNI**：不做用户系统、不做历史记录持久化、不做多工具（但预留可扩展的工具箱结构）。

## 3. 技术原理（简述）

水印由 CDN 在展示时叠加，并非烧进原图。小红书对同一张图维护两套 CDN：

- `sns-webpic-*.xhscdn.com`：App/网页展示用，降分辨率 + 水印，URL 带 `!nd_dft_wlteh_jpg_3` 处理后缀。
- `sns-img-*.xhscdn.com`：源站，原始分辨率、无水印。

两者共用同一个 `fileId`。解析笔记详情页中的 `window.__INITIAL_STATE__` 拿到 `imageList[].fileId`，拼源站 URL `https://sns-img-qc.xhscdn.com/{fileId}?imageView2/format/png` 即得无水印原图。详见 `docs/技术原理.md`。

### 关键 CDN 行为（已实测）

- 源站 CDN **CORS 开放**（`access-control-allow-origin: *`）。
- 源站 CDN **有防盗链**：伪造非小红书域的 `Referer` 返回 `403`，无 `Referer` 返回 `200`。
- 结论：浏览器直接 `<img src>` 会带本站 Referer，易被 403；因此**图片统一走后端代理**（后端请求 CDN 时不带 Referer）。

## 4. 架构

### 4.1 部署形态

单容器，多阶段 Dockerfile：

- **阶段一** `node:24-alpine`（本地已有）：构建 React 前端为静态文件。
- **阶段二** `python:3.12-slim-bookworm`（本地已有）：安装 FastAPI 及依赖，拷入前端静态产物，由 FastAPI 同时托管前端页面（`StaticFiles`）与 API。

`docker-compose.yml` 单 service，端口映射 `0.0.0.0:8823:8000`（宿主机 8823 → 容器 8000，可在 compose 中调整），`logs/` 目录挂载到宿主机持久化。

选择单容器的理由：无状态、无 DB、前后端同源可省去跨域配置，个人 LAN 工具运维最省心；多容器（nginx + 后端）在此规模是过度设计，且本地无 nginx 镜像。

### 4.2 后端（FastAPI）

模块划分（每个文件单一职责）：

- `app/parser.py`：链接解析。短链 302 还原 → 带 `xsec_token` 抓详情页 → 正则提取 `__INITIAL_STATE__` → 递归找 `imageList` → 收集去重 `fileId`（重构自 `xhs_dl.py`）。
- `app/cdn.py`：CDN 拉取。多源站容灾（`sns-img-qc/bd/hw/qn`），不带 Referer，流式返回字节。
- `app/logging_conf.py`：结构化日志配置（按天滚动到 `logs/access.log`）。
- `app/main.py`：FastAPI 应用、路由、静态托管、异常处理。

API：

| 方法 | 路径 | 入参 | 返回 |
|---|---|---|---|
| POST | `/api/parse` | `{ "share": "<分享文案或链接>" }` | `{ note_id, title, author, images: [{ index, file_id, width, height, url }] }`，其中 `url` 为后端代理地址 `/api/image?file_id=...` |
| GET | `/api/image` | `file_id`（query），`download`（可选，`1` 则加 `Content-Disposition`） | 图片字节流（`image/png`） |
| POST | `/api/package` | `{ "file_ids": [...], "title": "<可选，用于命名>" }` | ZIP 字节流（`application/zip`），文件名 `笔记标题.zip` |

### 4.3 前端（React + Vite + Motion）

- **工具箱外壳**：首页「cynic 工具箱」，卡片网格列出工具（当前一张卡：小红书无水印下载）。路由到工具页。结构预留扩展：新增工具 = 加一张卡 + 一个路由。
- **工具页**：
  - 顶部：输入框 + 右侧「解析」按钮。
  - 解析后：下方网格展示图片，每张 hover 显示「下载」按钮；页面显著位置有「打包下载全部」主按钮。
  - 状态：解析中显示连续反馈（骨架/进度），错误内联提示。

## 5. 数据流

```
粘贴分享文案 → POST /api/parse
   后端: 短链302还原 → 带 xsec_token 抓详情页 → 提取 file_id 列表 → 写审计日志
   → 返回图片元数据（代理 URL）
前端渲染网格 <img src="/api/image?file_id=...">
单张下载 → GET /api/image?file_id=...&download=1
一键打包 → POST /api/package({file_ids,title}) → 后端逐张拉取打 ZIP 流 → 浏览器保存
```

## 6. 错误处理

- 文案无链接 / 链接非法 → `400`，提示「未识别到小红书链接」。
- `xsec_token` 过期 / 命中登录墙（详情页无 `__INITIAL_STATE__` 或 imageList 为空）→ `422`，提示「链接已失效，请重新复制分享链接」。
- 单张图 CDN `403`/超时 → 自动轮询其他源站，全失败该张标记失败（打包时跳过并记录）。
- 详情页结构变化解析失败 → `502`，提示「解析失败，接口可能已变更」。

## 7. 日志留痕（审计）

无 DB，使用结构化日志。每次请求写一行 JSON 到 `logs/access.log`（`TimedRotatingFileHandler` 按天滚动）：

字段：`timestamp`、`client_ip`、`action`（parse/image/package）、`input`（原始链接，parse 时）、`note_id`、`image_count`、`status`、`duration_ms`。

`logs/` 挂载到宿主机，容器重建不丢日志。

## 8. Apple 风格交互落地（依据 apple-design 技能）

- **响应**：按钮按下即反馈（`:active` `scale(0.97)`，~100ms），不等释放。
- **弹簧动效**：默认临界阻尼（`bounce: 0`, `duration: 0.3~0.4`）；图片入场、卡片进入用；仅在有 momentum 的交互（如列表滑入）用轻微 bounce。
- **可打断**：动画从当前呈现值开始，可中途打断，不锁输入。
- **材质与层次**：顶部工具栏半透明 `backdrop-filter: blur()`，内容从下滚过；大表面更强模糊 + 更深阴影。
- **排版**：系统字体，大标题负字距（`-0.02em`）紧凑行高，正文字距近 `0`、行高舒适。
- **无障碍**：`prefers-reduced-motion` 用淡入淡出替代位移弹簧；`prefers-reduced-transparency` 降透明改实底。

## 9. 项目结构

```
nowm/
├── README.md                 # 项目说明（部署/使用）
├── docs/
│   ├── 技术原理.md            # 无水印原理与技术路线
│   └── superpowers/specs/
│       └── 2026-07-16-xhs-nowm-service-design.md   # 本设计文档
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── parser.py
│   │   ├── cdn.py
│   │   └── logging_conf.py
│   └── requirements.txt
├── frontend/                 # Vite + React
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── pages/{Home.tsx, XhsTool.tsx}
│       └── components/...
├── Dockerfile                # 多阶段构建
├── docker-compose.yml
└── .gitignore
```

CLI 脚本 `xhs_dl.py` 不纳入仓库。

## 10. 成功标准

- 局域网内手机/电脑打开页面，粘贴分享链接可解析出全部图片并展示。
- 单张下载、一键打包 ZIP 均得到无水印原图。
- `docker compose up -d` 一键起服务，重启后日志保留。
- 交互符合 Apple 风格设计要点（响应即时、动效流畅可打断、材质层次清晰）。
