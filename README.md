<div align="center">

# 📡 AI Daily Digest

**每天 5 分钟，掌握 AI 领域最值得关注的动态。**

全自动采集 · AI 智能筛选与总结 · 中英双语 · 重要性评分 · 语音播报 · 每日定时发布

### 👉 [**在线阅读：jimmuji.github.io/ai-daily-digest**](https://jimmuji.github.io/ai-daily-digest/) 👈

[![Visit Site](https://img.shields.io/badge/🌐_在线网站-访问-2ea043?style=for-the-badge)](https://jimmuji.github.io/ai-daily-digest/)
[![Podcast](https://img.shields.io/badge/🎧_在小宇宙收听-播客-9333ea?style=for-the-badge)](https://www.xiaoyuzhoufm.com/podcast/6a325e149357568efe4741ef)

[![Daily Digest](https://github.com/Jimmuji/ai-daily-digest/actions/workflows/daily.yml/badge.svg)](https://github.com/Jimmuji/ai-daily-digest/actions/workflows/daily.yml)
![GitHub last commit](https://img.shields.io/github/last-commit/Jimmuji/ai-daily-digest)
![GitHub stars](https://img.shields.io/github/stars/Jimmuji/ai-daily-digest?style=social)

[**🌐 在线网站**](https://jimmuji.github.io/ai-daily-digest/) · [**🎧 播客订阅**](https://www.xiaoyuzhoufm.com/podcast/6a325e149357568efe4741ef) · [**📖 日报存档**](daily/) · [**⚙️ 快速部署**](#-快速开始) · [**💡 设计理念**](#-为什么做这个)

</div>

---

## 🤔 为什么做这个

AI 领域每天产出大量信息——新论文、新模型、新产品、新融资，散落在 HuggingFace、GitHub、TechCrunch、36Kr 等几十个平台上。

**问题是**：手动逐个刷太耗时间，全靠 AI 自动筛又不放心。

**AI Daily Digest** 的做法是：
> 脚本负责从多个源抓取原始数据，AI 负责筛选去重 + 生成结构化摘要。全程零人工干预，每天自动跑，结果直接存到 GitHub 仓库里。

---

## ✨ 它能做什么

```
📥 数据采集（免费 API / RSS）
 │
 ├── 📄 HuggingFace Daily Papers     ← 每日热门 AI 论文
 ├── 🔧 GitHub Trending (OSSInsight)  ← 热门 AI 开源项目
 ├── 📰 36Kr AI / SSPAI              ← 中文 AI 新闻
 └── 📰 TechCrunch / The Verge       ← 英文 AI 新闻
 │
 ▼
🧠 AI 智能处理（DeepSeek）
 │
 ├── 从 ~60 条原始资讯中筛选 10-15 条精华
 ├── 去重、按类别分组（新闻 / 论文 / 开源项目）
 ├── 每条 2-3 句话总结，保留关键信息和原文链接
 ├── 给每条资讯标注重要性：★☆☆☆☆ - ★★★★★
 ├── 生成 "今日观察" 趋势点评
 ├── 同一次调用产出中英双语两份简报
 └── 改写成口播稿（电台风格）
 │
 ▼
📤 自动发布
 │
 ├── 生成中/英文 Markdown → 存入 daily/（{date}.md + {date}.en.md）
 ├── 语音合成 MP3（edge-tts，免费神经网络语音）→ docs/audio/
 ├── 构建静态站点 → docs/（首页、每日页、全文搜索、热词、播客页）
 ├── 生成播客 RSS 订阅源 → docs/podcast.xml（可在小宇宙 / Apple 播客订阅）
 ├── 渲染社交封面图 → docs/covers/{date}.png（1080×1440，可直接发小红书）
 └── 保存原始数据 JSON → data/，方便追踪来源
```

---

## 🌟 网站与收听

不只是 Markdown 存档，[在线站点](https://jimmuji.github.io/ai-daily-digest/) 还提供：

- **🌐 中英双语**：一键切换中文 / English，正文与界面同步切换（旧日报无英文时自动回退中文）。
- **🎧 语音播报**：每期由 AI 改写成口播稿并合成 MP3，网页内置播放器，支持锁屏 / 车机控制（MediaSession）。
- **📻 播客订阅**：标准 RSS 订阅源，[在小宇宙收听](https://www.xiaoyuzhoufm.com/podcast/6a325e149357568efe4741ef)，或在 Apple 播客 / Pocket Casts 添加 `…/podcast.xml`，每天通勤自动下载。
- **🔍 全文搜索**：跨全部历史日报即时搜索（中英皆可）。
- **🔥 热词趋势**：近 7 天高频话题/公司标签，点击直达相关日报。
- **🌓 浅色 / 深色主题**：跟随系统或手动切换，偏好本地记忆。
- **📱 可安装为 App**：支持添加到手机 / 桌面主屏幕，独立窗口打开，最近 7 期自动离线缓存，地铁没信号也能读。

---

## 📱 装成 App

站点本身就是一个 PWA，无需应用商店：

- **iPhone / iPad**：Safari 打开站点 → 底部「分享」→ **添加到主屏幕**。
- **Android / 桌面 Chrome、Edge**：页面底部会弹出「安装」提示，或用地址栏右侧的安装图标。

装好之后：图标直达、全屏无浏览器地址栏、最近 7 期日报与最近听过的 5 期音频离线可用；断网时打开未缓存的日期会显示离线页并列出本地已有的期数。

### 📦 JSON API

给 App / 脚本 / 第三方客户端用的结构化数据，无需解析 HTML：

| 接口 | 内容 |
|------|------|
| [`api/index.json`](https://jimmuji.github.io/ai-daily-digest/api/index.json) | 全部期号列表：日期、今日标题、条目数、音频时长、当期 3 条重点 |
| [`api/{date}.json`](https://jimmuji.github.io/ai-daily-digest/api/2026-07-29.json) | 单期全文：今日标题 + 2 条备选、分类、摘要、核心价值、星级、来源链接，中英各一份 |

「今日标题」是每期一句 20 字以内的概括，直接可用作社交媒体标题；`headline_alt` 是两条备选。
早于该功能上线的日报没有这一字段，此时 `headline` 回落为当期星级最高的那条标题，并标记 `headline_is_fallback: true`。

```bash
# 最新一期的日期
curl -s https://jimmuji.github.io/ai-daily-digest/api/index.json | jq -r .latest

# 拉取该期全文
curl -s https://jimmuji.github.io/ai-daily-digest/api/2026-07-29.json | jq '.zh.categories[].name'
```

所有 URL 均相对于站点根地址，客户端只需记住一个 base URL。

---

## 📋 日报示例

> 以下为 [2026-04-14 日报](daily/2026-04-14.md) 的部分摘录：

### 📰 行业新闻
1. **OpenAI 收购个人理财初创公司 Hiro**：OpenAI 正将财务规划能力整合进 ChatGPT 中，拓展其应用边界。
   - 重要性：★★★★☆ / 5
   - 为什么重要：这代表通用 AI 助手正在进入高价值垂直场景。
   - 来源：[TechCrunch AI](https://techcrunch.com/category/artificial-intelligence/)
2. **微软测试类 OpenClaw 的自主 AI 助手**：微软正研究将自主运行功能集成到 Copilot 中，旨在让其能为企业用户全天候自动完成任务...

### 📄 重要论文
1. **SPEED-Bench：投机解码的统一多样化基准**：投机解码是加速大模型推理的关键技术，该研究提出了支持吞吐量评估的新基准...

### 🔧 开源项目
1. **Hermes Agent 发布 0.9.0**：支持原生微信 Callback 功能，使智能体能够更好地与微信生态集成...

### 💡 今日观察
> 今日资讯呈现出 AI 领域"落地加速"与"生态分化"并行的鲜明特点...

---

## 🚀 快速开始

只需 3 步，Fork 后就能跑：

### 1. Fork 本仓库

点击右上角 **Fork** 按钮。

### 2. 配置 API Key

进入你 Fork 的仓库 → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**：

| Secret 名称 | 值 | 说明 |
|-------------|-----|------|
| `API_KEY` | 你的 API Key | 默认使用 [DeepSeek](https://platform.deepseek.com/)（中文友好） |

> 💡 也支持 OpenAI 或任何兼容 API。可以在 **Settings → Secrets and variables → Actions → Variables** 里设置 `API_BASE_URL` 和 `API_MODEL`。

### 3. 启用 GitHub Actions

进入 **Actions** 标签页 → 点击 **I understand my workflows, go ahead and enable them**。

搞定！每天北京时间 **08:00** 会自动运行。也可以点击 **Run workflow** 手动触发。

---

## 🏗️ 项目结构

```
ai-daily-digest/
├── .github/workflows/
│   └── daily.yml            # GitHub Actions 定时任务
├── scripts/
│   ├── main.py              # 入口：采集 → 总结 → 语音 → 建站
│   ├── sources.py           # 数据源：HuggingFace / GitHub / RSS
│   ├── summarize.py         # AI 总结：DeepSeek，中英双语单次调用
│   ├── audio.py             # 口播稿 + edge-tts 语音合成 + 旧音频清理
│   ├── generate_site.py     # 静态站点 + 搜索/热词/播放器 + 播客 RSS + API/PWA
│   ├── cover.py             # 每日社交封面图（1080×1440，headless Chrome 渲染）
│   ├── brandmark.py         # 品牌标识几何定义（棱镜分光）
│   └── make_icons.py        # 一次性：渲染 logo 与 App 图标
├── daily/                   # 📰 每日日报（{date}.md + {date}.en.md）
│   ├── 2026-04-14.md
│   └── ...
├── data/                    # 🔎 每日原始素材（JSON，便于追踪和调试）
│   └── 2026-04-14.raw.json
├── docs/                    # 🌐 GitHub Pages 站点（自动生成）
│   ├── index.html           #    首页（最新一期 + 归档 + 热词）
│   ├── daily/*.html         #    每日页面
│   ├── audio/*.mp3          #    🎧 语音播报（仅保留最近 15 期）
│   ├── podcast.xml          #    📻 播客 RSS 订阅源
│   ├── podcast.xsl          #    浏览器内美化播客页的样式表
│   ├── podcast-cover.png    #    播客封面
│   ├── search-index.json    #    全文搜索索引
│   ├── api/                 #    📦 JSON API（index.json + 每期一个文件）
│   ├── covers/              #    🖼 每日社交封面图（保留最近 30 期）
│   ├── icons/               #    App 图标（192/512/maskable/apple-touch）
│   ├── manifest.webmanifest #    PWA 应用清单
│   ├── sw.js                #    Service Worker：离线缓存
│   └── offline.html         #    断网时的兜底页
├── brand/                   # 🎨 logo 源文件与社交头像
├── requirements.txt
└── README.md
```

---

## 🔧 自定义配置

### 更换 AI 模型

在 workflow 的环境变量中设置：

```yaml
env:
  API_KEY: ${{ secrets.API_KEY }}
  API_BASE_URL: ${{ vars.API_BASE_URL || 'https://api.deepseek.com' }}
  API_MODEL: ${{ vars.API_MODEL || 'deepseek-chat' }}
```

例如使用 OpenAI 时，把仓库变量 `API_BASE_URL` 设为 `https://api.openai.com/v1`，`API_MODEL` 设为 `gpt-4o-mini` 或其他可用模型。

### 重要性评分

脚本会先根据来源类别、关键词和大公司/高影响信号给每条素材一个 `importance_hint`。AI 生成日报时会结合原始内容重新判断，并在每条资讯下输出：

```markdown
- 重要性：★★★★☆ / 5
- 为什么重要：说明对开发者、产品、研究或产业的影响。
- 来源：[Source Name](URL)
```

### 添加数据源

编辑 `scripts/sources.py`，在 `RSS_SOURCES` 列表中添加新的 RSS 源：

```python
RSS_SOURCES = [
    ("https://rsshub.rssforever.com/36kr/search/articles/ai", "36Kr AI"),
    ("https://your-new-source.com/rss", "New Source"),  # ← 加这里
]
```

### 修改发布时间

编辑 `.github/workflows/daily.yml` 中的 cron 表达式：

```yaml
schedule:
  - cron: '0 0 * * *'   # UTC 00:00 = 北京时间 08:00
  - cron: '0 12 * * *'  # 加一行 = 每天跑两次
```

### 更换语音音色

语音用 [edge-tts](https://github.com/rany2/edge-tts)（免费，无需 Key）。默认音色为新闻主播风格 `zh-CN-YunyangNeural`，可用仓库变量 `AUDIO_VOICE` 覆盖（如 `zh-CN-XiaoxiaoNeural`、`zh-CN-YunxiNeural`）。没有配置 `API_KEY` 时会自动退回「确定性朗读稿」，保证仍有音频产出。音频默认只保留最近 15 期以控制仓库体积。

---

## 🗺️ Roadmap

- [x] 核心 pipeline：数据采集 → AI 总结 → 自动发布
- [x] 每条资讯保留来源链接
- [x] 重要性评分 / 标星
- [x] 保存原始抓取数据 JSON
- [x] GitHub Pages 静态站点（卡片布局 + 浅色/深色主题）
- [x] 全文搜索 + 热词趋势追踪
- [x] 中英双语简报与界面切换
- [x] 语音播报（edge-tts）+ 播客 RSS 订阅源
- [x] 更多数据源（Hacker News、机器之心、量子位、Wired、IEEE 等）
- [x] JSON API + PWA（可安装、离线阅读）
- [x] 每期一句「今日标题」+ 自动生成社交封面图
- [ ] 每日推送通知（Web Push）
- [ ] 上架 App Store / Play（Capacitor 套壳，见 [APP.md](APP.md)）
- [ ] 英文语音版
- [ ] Telegram 推送
- [ ] 每周回顾报告

---

## 🤝 Contributing

欢迎贡献！无论是新增数据源、优化 Prompt、改进输出格式，还是修 Bug，都非常感谢。

1. Fork 本仓库
2. 创建你的分支：`git checkout -b feature/xxx`
3. 提交更改：`git commit -m 'Add xxx'`
4. 推送到远程：`git push origin feature/xxx`
5. 提交 Pull Request

---

## 📄 License

MIT License - 随便用，注明出处即可。

---

<div align="center">

**如果觉得有用，欢迎 ⭐ Star 支持一下！**

</div>
