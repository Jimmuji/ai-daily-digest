# 把 AI Daily Digest 做成 App

站点已经是一个可安装的 PWA。这份文档记录**已经做完的部分**、**还差什么**，以及每一步真实的成本与风险。

---

## ✅ 阶段一：PWA（已完成）

无需应用商店、无需服务器，站点本身即可安装到主屏幕。

| 产物 | 说明 |
|------|------|
| `docs/manifest.webmanifest` | 应用名、图标、启动地址、独立窗口显示 |
| `docs/icons/*` | 192 / 512 / maskable / apple-touch，由 `scripts/make_icons.py` 从播客封面生成 |
| `docs/sw.js` | Service Worker：页面网络优先、JSON 先读缓存再更新、音频缓存最近 5 期、激活时预热最近 7 期 |
| `docs/offline.html` | 断网打开未缓存日期时的兜底页，并列出本地已缓存的期数 |
| `docs/api/*.json` | 结构化数据源，客户端不必解析 HTML |
| 安装提示条 | Chrome/Edge 用系统安装弹窗；iOS Safari 显示「分享 → 添加到主屏幕」引导，可关闭且只提示一次 |

缓存策略在 `scripts/generate_site.py` 的 `SW_JS` 里，改 `WARM_DAYS`（预热期数）和 `MEDIA_KEEP`（音频保留期数）即可调整占用空间。当前默认约 7 篇页面 + 5 期音频 ≈ 12 MB。

**验证方式**：本地 `cd docs && python3 -m http.server`，用 Chrome 打开，DevTools → Application 里能看到 Service Worker 与三个 Cache Storage；关掉服务器后仍可阅读最近 7 期。

---

## 📌 阶段二：每日推送通知（未做）

这是 PWA 与「真 App」体验差距最大的一块，也是唯一需要引入服务端的功能。静态站点无法自己发推送——必须有人保存订阅、有人在发布后调用推送服务。

需要三样东西：

1. **VAPID 密钥对**：`npx web-push generate-vapid-keys`，公钥进前端，私钥进 GitHub Secrets。
2. **订阅存储**：浏览器订阅后拿到一个 endpoint，需要存起来。GitHub Pages 是纯静态的，存不了，最省事的是 Cloudflare Workers + KV（免费额度足够，每天几百个订阅者绰绰有余）。
3. **发送端**：`daily.yml` 生成日报后多一步，调用 Worker，遍历订阅推送标题 + 当期重点。

iOS 的限制要提前知道：Web Push 需要 iOS 16.4 以上，**且用户必须先「添加到主屏幕」**，在 Safari 标签页里打开是收不到的。Android / 桌面 Chrome 无此限制。

不想自建的话，OneSignal 免费版可以顶掉第 2、3 步，代价是引入第三方 SDK 和它的数据收集。

**预估**：自建方案约半天，含调试。

---

## 📌 阶段三：上架应用商店（未做）

只有在「想让别人搜到并下载」时才值得做。功能上，商店版相比 PWA 只多了原生推送权限和商店入口。

**技术路线**：Capacitor 套壳，复用现有 `docs/`，不重写前端。

```bash
npm init -y && npm i @capacitor/core @capacitor/cli
npx cap init "AI Daily Digest" io.github.jimmuji.aidigest --web-dir=docs
npx cap add ios && npx cap add android
```

推送用 `@capacitor/push-notifications`（APNs / FCM），比 Web Push 可靠，但需要重新配一套证书。

**真实成本与风险**：

- Apple 开发者账号 **99 美元/年**，Google Play **25 美元**一次性。
- 苹果审核指南 **4.2 Minimum Functionality**：纯网页套壳是常见拒审理由。要过审，得让 App 明显不只是个网页——离线阅读、后台音频播放、推送、原生播放器，这几样最好都在，并在审核备注里说明。
- 每次内容更新不需要重新提交（内容是远程的），但外壳本身有更新时仍要走审核。

**建议**：先把 PWA 推给身边的人用一段时间。如果留存不错、有人主动问「有没有 App」，再花这笔钱和时间。

---

## 📌 阶段四：原生客户端（可选，投入产出比最低）

真要写原生（SwiftUI / React Native），数据层已经就绪：读 `api/index.json` 拿列表，读 `api/{date}.json` 拿全文，音频直接用 `audio/{date}.mp3`，播客用 `podcast.xml`。

只有当你想做 PWA 做不到的事情时才值得——例如小组件、Live Activity、系统级音频队列、Watch 端。否则维护两套 UI 得不偿失。

---

## 需要你本人操作的事项

以下几件我做不了，需要你自己的账号或密钥：

- [ ] 部署后在真机上装一次，确认 iOS「添加到主屏幕」的图标与启动页正常
- [ ] 想做推送：注册 Cloudflare 账号，生成 VAPID 密钥，把私钥存进仓库 Secrets
- [ ] 想上架：注册 Apple / Google 开发者账号
- [ ] 可选：绑定自定义域名（`digest.yourdomain.com`），比 `jimmuji.github.io/ai-daily-digest/` 更像一个产品
