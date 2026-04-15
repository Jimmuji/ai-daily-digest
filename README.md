<div align="center">

# 📡 AI Daily Digest

**每天 5 分钟，掌握 AI 领域最值得关注的动态。**

全自动采集 · AI 智能筛选与总结 · 重要性评分 · 每日定时发布

[![Daily Digest](https://github.com/Jimmuji/ai-daily-digest/actions/workflows/daily.yml/badge.svg)](https://github.com/Jimmuji/ai-daily-digest/actions/workflows/daily.yml)
![GitHub last commit](https://img.shields.io/github/last-commit/Jimmuji/ai-daily-digest)
![GitHub stars](https://img.shields.io/github/stars/Jimmuji/ai-daily-digest?style=social)

[**📖 查看最新日报**](daily/) · [**⚙️ 快速部署**](#-快速开始) · [**💡 设计理念**](#-为什么做这个)

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
 └── 生成 "今日观察" 趋势点评
 │
 ▼
📤 自动发布
 │
 ├── 生成 Markdown → 存入 daily/ 目录
 └── 保存原始数据 JSON → 存入 data/ 目录，方便追踪来源
```

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
│   ├── main.py              # 入口：采集 → 总结 → 保存
│   ├── sources.py           # 数据源：HuggingFace / GitHub / RSS
│   └── summarize.py         # AI 总结：调用 DeepSeek API
├── daily/                   # 📰 每日生成的日报（Markdown）
│   ├── 2026-04-14.md
│   └── ...
├── data/                    # 🔎 每日原始素材（JSON，便于追踪和调试）
│   ├── 2026-04-14.raw.json
│   └── ...
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

---

## 🗺️ Roadmap

- [x] 核心 pipeline：数据采集 → AI 总结 → 自动发布
- [x] 每条资讯保留来源链接
- [x] 重要性评分 / 标星
- [x] 保存原始抓取数据 JSON
- [ ] GitHub Pages 静态站点
- [ ] RSS 输出
- [ ] 趋势追踪（"本周 Agent 相关新闻出现 12 次"）
- [ ] 邮件 / Telegram 推送
- [ ] 更多数据源（Reddit、Hacker News、ArXiv）
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
