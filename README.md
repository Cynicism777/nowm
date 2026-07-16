# nowm · cynic 工具箱

一个自托管的小工具集合，当前收录：

- **小红书无水印图片下载**：粘贴小红书分享链接，解析并展示笔记全部图片，支持单张下载与一键打包 ZIP，全部为无水印原图。

前后端分离，后端 FastAPI，前端 React（Vite + Motion），单容器 Docker 部署，无数据库，仅用日志做留痕/审计。定位为局域网内随时随地使用的个人工具箱。

## 技术原理

图片水印由小红书 CDN 在展示时叠加，并非烧进原图；换用源站 CDN 域名 + 图片的 `fileId` 即可取到无水印原图。完整原理与技术路线见 [`docs/技术原理.md`](docs/技术原理.md)。

## 架构

- **后端**（`backend/`）：FastAPI 提供解析、图片代理、打包三个 API，并托管前端静态页面。因源站 CDN 有防盗链（非小红书 Referer 会被 403），图片统一由后端代理拉取。
- **前端**（`frontend/`）：React + Vite，Apple 风格流畅交互；工具箱首页 + 工具页。
- **部署**：多阶段 Dockerfile（`node` 构建前端 → `python` 运行），`docker compose` 单服务，服务绑定 `0.0.0.0`，局域网可访问。

详细设计见 [`docs/superpowers/specs/2026-07-16-xhs-nowm-service-design.md`](docs/superpowers/specs/2026-07-16-xhs-nowm-service-design.md)。

## 目录结构

```
.
├── README.md
├── docs/
│   ├── 技术原理.md
│   └── superpowers/specs/            # 设计文档
├── backend/                          # FastAPI 服务
│   ├── app/
│   └── requirements.txt
├── frontend/                         # Vite + React 前端
├── Dockerfile                        # 多阶段构建
└── docker-compose.yml
```

## 快速开始

```bash
docker compose up -d --build
```

默认监听 `0.0.0.0:8823`（宿主机端口可在 `docker-compose.yml` 调整），浏览器访问 `http://<服务器IP>:8823`。

日志写入 `./logs/access.log`（挂载自容器 `/app/logs`），可用于留痕/审计。

停止服务：`docker compose down`（镜像默认保留，加 `--rmi local` 可一并清理镜像）。

## 免责声明

本工具仅去除平台叠加的水印，不去除原作者画在图上的水印。下载内容版权归原作者所有，请仅用于个人学习，转载/商用需获得授权。
