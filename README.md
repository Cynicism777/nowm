# nowm

cynic 的个人工具站。自托管的小工具集合，当前收录：

- **小红书无水印图片下载**：粘贴小红书分享链接，解析并展示笔记全部图片，全部为无水印原图；保存按设备自适应——手机存相册、PC 单张下载或一键打包 ZIP。

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

## 访问控制（邀请链接）

首次部署时复制环境变量示例，并为邀请令牌和会话密钥分别生成独立的随机值：

```bash
cp .env.example .env
openssl rand -hex 32  # 填入 INVITE_TOKEN
openssl rand -hex 32  # 填入 SESSION_SECRET
docker compose up -d --build
```

将邀请链接 `https://<你的域名>/?invite=<INVITE_TOKEN>` 发给获准访问的用户。局域网调试可使用
`http://<IP>:8823/?invite=<INVITE_TOKEN>`，此时须在 `.env` 中设置 `COOKIE_SECURE=false`。

需要吊销访问时，替换 `INVITE_TOKEN` 可让旧邀请链接失效；替换 `SESSION_SECRET` 可让全部现有 Cookie
立即失效。修改后运行 `docker compose up -d` 应用新配置。

## HTTPS 与手机存相册

保存图片按设备能力自适应：**手机走系统分享面板可直接存入相册，PC 走文件/ZIP 下载**。
其中手机端「保存到相册」依赖浏览器 Web Share API，该 API 仅在**安全上下文（HTTPS）**下可用。

本服务默认由你的网关 / 反向代理统一终结 HTTPS，容器内保持 HTTP（`uvicorn` 已开启
`--proxy-headers --forwarded-allow-ips=*`，可正确识别转发协议与客户端 IP）。

- 经 **HTTPS** 访问：单张「保存」、批量「保存全部」会弹系统分享面板，可存入相册。
- 经明文 **HTTP** 访问：自动回退为文件下载 / ZIP 下载，功能不受影响，但无法直接存相册。

## 免责声明

本工具仅去除平台叠加的水印，不去除原作者画在图上的水印。下载内容版权归原作者所有，请仅用于个人学习，转载/商用需获得授权。
