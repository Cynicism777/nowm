# 图片保存自适应（手机存相册 / PC 下载）— 设计文档

- 日期：2026-07-17
- 项目：nowm（cynic 工具箱）
- 关联：`2026-07-16-xhs-nowm-service-design.md`

## 1. 背景与问题

当前工具箱 UI 采用移动优先的响应式设计，但「保存图片」与「打包下载」两个功能偏 PC：
单张走 `<a download>`、批量走后端 ZIP。手机用户拿到的是**文件**而非**相册照片**，ZIP 在手机上更是几乎无用。
表面看是「UI 偏手机、下载偏 PC」的矛盾。

**真正的判断**：这不是 UI 矛盾，而是「保存」这一个动作在不同设备上的最优实现不同。UI 保持一套响应式即可，
只需把「保存」从 UI 中抽离为一个**保存策略层**，由**运行时能力探测**选择实现。

## 2. 目标与约束

- 手机（安全上下文 + 支持文件分享）：单张 / 批量都能通过系统分享面板**存到相册**。
- PC（或不支持文件分享）：单张下载文件、批量下载 ZIP，保持现状体验。
- UI 只有一套响应式；设备差异**全部收敛到一个前端模块** `frontend/src/save.ts`。
- 后端 API 不变；仅补充反向代理友好配置。
- YAGNI：不引入前端单测框架（仓库前端现无测试，沿用「构建 + 手动端到端」验证）。

## 3. 关键技术约束（已论证）

1. **Web Share API 需安全上下文**：`navigator.share({files})` 仅在 HTTPS / localhost 可用。
   本服务由**用户既有网关**统一做 HTTPS 终结，仓库不管证书；后端仅需识别转发头。
   **硬约束**：必须经网关走 HTTPS 访问，否则手机端「保存到相册」不可用（能力探测会自动回退到下载）。
2. **瞬时用户激活（transient activation）**：`navigator.share` 必须由一次用户点击直接触发，
   且一次点击只能弹一次。**「点一次按钮自动逐张弹分享」不可靠**（第二次起抛 `NotAllowedError`）。
   因此批量走「一次性多图分享」，不做自动逐张。
3. **多图分享支持面**：iOS Safari、Android Chrome 均支持一次性多图分享
   （`canShare({files:[多张]})` 返回 true），覆盖主要手机场景。
4. **激活时效**：`share` 前需 `fetch` 图片字节再包 `File`，若 `fetch` 太慢会超出激活窗口。
   缓解：图片已在页面以 `<img src>` 展示，`fetch` 同源代理会命中浏览器 HTTP 缓存，通常极快；
   失败时回退到下载。

## 4. 架构

```
UI 组件 (ImageGrid / 批量按钮)
        │  仅调用 saveOne() / saveAll()，不含任何设备判断；文案按能力探测切换
        ▼
保存策略层  frontend/src/save.ts
        │  运行时探测 supportsFileShare / canShare({files}) 决定分支
        ├── 支持文件分享 + 多图可分享 → navigator.share({files}) → 系统面板 → 存相册
        ├── 支持文件分享但不支持多图（罕见）→ 批量返回 "guide"，提示逐张保存
        └── 不支持文件分享（PC）→ <a download>（单张）/ 后端 ZIP（批量）
        ▼
后端图片代理 /api/image、打包 /api/package（不变）
```

设备差异只活在 `save.ts` 一个文件；UI 与后端都不含分支判断。未来新增设备策略（如桌面 PWA 文件系统 API）只改这一层。

## 5. `save.ts` 接口

```ts
export function supportsFileShare(): boolean;          // 探测是否支持单文件分享（决定文案与分支）
export async function saveOne(im: ImageItem): Promise<void>;
export type SaveAllResult = { kind: "shared" | "zip" | "guide" };
export async function saveAll(images: ImageItem[], title: string): Promise<SaveAllResult>;
```

行为：

- `supportsFileShare()`：`navigator.canShare` 存在且对一张探针 `File` 返回 true。
- `saveOne(im)`：`fetch(im.url)` → `File`；若 `canShare({files:[file]})` 则 `navigator.share`，
  用户取消（`AbortError`）视为正常返回；分享失败或不支持 → `<a download>` 下载。
- `saveAll(images, title)`：
  - 若 `supportsFileShare()`：`fetch` 全部 → 若 `canShare({files})`（多图）则 `navigator.share`，
    返回 `shared`（`AbortError` 亦返回 `shared`，即用户主动取消不报错）；
    多图不支持 → 返回 `guide`（不下载，由 UI 提示逐张保存）。
  - 否则（PC）：调用现有 `downloadZip`，返回 `zip`。

## 6. UI 变更

- `ImageGrid`：单图角标按钮由 `<a>` 改为按钮，`onClick` 调 `saveOne(im)`；
  文案：`supportsFileShare()` 为真显示「保存」，否则「下载」。
- `XhsTool`：批量按钮 `onClick` 调 `saveAll`；
  文案：能分享显示「保存全部」，否则「打包下载 ZIP」；
  处理返回：`guide` → 内联提示「请用每张图片上的「保存」按钮逐张存到相册」。
- 保持 Apple 风格：按钮沿用现有 `:active` 与动效，不新增视觉元素。

## 7. 后端 / 部署变更

- `uvicorn` 启动加 `--proxy-headers --forwarded-allow-ips=*`，在网关后正确识别客户端与协议。
  改动落在 `Dockerfile` 的 `CMD`。
- 文档补充 HTTPS 硬约束说明（`README.md` 与本设计）。

## 8. 错误与边界

- `fetch` 图片失败：`saveOne` 抛错由 UI 内联提示；`saveAll` 分享路径失败回退提示。
- 用户在系统面板取消分享：`AbortError`，视为正常，不报错。
- 非安全上下文（http）：`navigator.canShare` 不存在或返回 false → 自动走下载/ZIP，功能不 crash。

## 9. 成功标准

- HTTPS 访问下，手机点单张「保存」→ 系统面板可存相册；点「保存全部」→ 一次面板可批量存相册。
- PC 访问，单张「下载」得到 png 文件；「打包下载 ZIP」得到 zip，行为同现状。
- http 访问下不报错，自动回退为下载/ZIP。
- 设备判断仅存在于 `save.ts`；`ImageGrid`/`XhsTool` 无设备条件分支（仅文案）。
