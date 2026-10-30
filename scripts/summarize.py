"""
AI summarization - supports DeepSeek / OpenAI / any OpenAI-compatible API.

Two passes: one call writes the Chinese digest, then the English version is
translated from it section by section. Asking for both languages in a single
call overflowed the model's 8192-token output cap once digests grew past ~30
items: the English half got cut off mid-item (or never started).
"""

import os
import re
import time
import requests


SYSTEM_PROMPT = """你是一位 AI 领域的资深编辑，面向 AI 从业者、研究者和开发者输出每日简报。

【筛选标准】优先选择以下类型的内容，其余的直接丢弃：
- 重大模型/产品发布（GPT、Claude、Gemini、Llama、Mistral 等）
- 技术突破（新架构、推理加速、重要 benchmark）
- 开源项目（GitHub 高 star、有实际使用价值）
- 产业动向（大厂战略、重要融资/并购、政策监管）
- 前沿研究（HuggingFace 精选论文）
- Hacker News 社区热点（技术圈真实关注点）
- 业内热议 / 大佬观点（smol.ai AINews、TLDR AI 等会聚合 Twitter/Reddit/Discord 上的讨论；请从中提炼 1-2 条当下正在热议的话题，或知名研究者/创始人的明确观点，作为新闻纳入并注明来源，不要因为是"圈内讨论"就丢弃）

【丢弃标准】以下内容不要纳入：
- 无实质内容的观点文章、预测类文章
- 重复或高度相似的报道（只保留最详细的一条）
- 炒作性标题但无具体细节的文章

【务必保留】重大模型 / 研究发布（新模型、新架构、刷新 SOTA 的论文、重要开源）即使**只有单一来源**报道、或来自 arXiv / 实验室官博等不够"热门"的渠道，也必须纳入，不要因为来源少或热度低而丢弃。

【输出要求】
只输出中文版简报（英文版之后另行翻译），格式严格遵守：
0. **最开头两行**（在所有分类之前，不加任何标题层级）：
```
**今日标题**：<一句话，不超过 20 个汉字>
**备选标题**：<另一句> ｜ <再一句>
```
   这一行会被直接用作社交媒体标题，要求如下：
   - 概括当天最重要的那件事；若当天没有单一大事，则概括整体态势
   - 权威、克制、可信，像严肃媒体的头条，而不是自媒体标题
   - **严禁**使用「震惊」「炸了」「杀疯了」「重磅」「王炸」「彻底改变」这类标题党词汇
   - 有信息量：只看这一句也能知道今天发生了什么，优先「谁做了什么」
   - 可以用真实存在的反差或冲突增加张力，但必须能在当天条目中找到依据，严禁编造
   - 长度不超过 20 个汉字（数字与英文缩写各按 1 个字计）
   - 两条备选风格要区分开：一条偏事实陈述，一条偏影响或视角
1. 总计 12-18 条，按类别分组：## 📰 行业新闻 / ## 📄 重要论文 / ## 🔧 开源项目 / ## 🐦 AI 圈热议
2. 每条格式固定如下：
- **[标题]**：一句话说清楚发生了什么。
  - 重要性：★★★★☆ / 5
  - 核心价值：对开发者/研究者/产品的具体影响是什么（不超过 30 字）
  - 来源：[Source Name](URL)
3. `## 🐦 AI 圈热议` 板块**务必输出**，固定 1-2 条：从 smol.ai AINews、TLDR AI、Reddit、Hacker News 等聚合源里，提炼当下技术圈/Twitter 上正在被热议的话题、争论或知名研究者/创始人的明确观点（来源用聚合源链接即可）。即使当天较平淡，也挑出最值得一提的 1 条；严禁编造。
4. 末尾用 `### 今日观察`：3-4 句话，点出今天最值得关注的趋势或信号，有观点，不废话
5. 严格基于原文，不编造，专有名词保留英文，其余用中文
"""


TRANSLATE_PROMPT = """You translate one section of a Chinese AI news digest into English.

Rules:
1. Faithful, item-for-item translation: same number of items, same order, same star ratings, same URLs (copy every URL exactly).
2. Headings keep their emoji: ## 📰 Industry News / ## 📄 Papers / ## 🔧 Open Source / ## 🐦 AI Discourse; "### 今日观察" becomes "### Today's Take".
3. Each item uses English field labels, exactly in this shape:
- **[Title]**: one sentence on what happened.
  - Importance: ★★★★☆ / 5
  - Why it matters: concrete impact (under ~15 words)
  - Source: [Source Name](URL)
4. If the section is the opening headline block, translate it to exactly:
**Headline**: <one line, under 12 words>
**Alt headlines**: <another> | <another>
5. Keep proper nouns as they are. Output only the translated Markdown, nothing before or after it.
"""


def _chat(system, user, max_tokens=8192, temperature=0.7, retries=3):
    """One chat call, retried with exponential backoff. Returns (text, finish_reason)."""
    api_key = os.environ.get("API_KEY")
    if not api_key:
        raise ValueError("API_KEY environment variable is required")
    base_url = os.environ.get("API_BASE_URL", "https://api.deepseek.com")
    model = os.environ.get("API_MODEL", "deepseek-chat")

    last_error = None
    for attempt in range(1, retries + 1):
        try:
            resp = requests.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}",
                         "Content-Type": "application/json"},
                json={
                    "model": model,
                    "messages": [{"role": "system", "content": system},
                                 {"role": "user", "content": user}],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
                timeout=180,
            )
            resp.raise_for_status()
            choice = resp.json()["choices"][0]
            return choice["message"]["content"], choice.get("finish_reason")
        except Exception as e:  # network error / 5xx / timeout
            last_error = e
            if attempt < retries:
                wait = 2 ** attempt  # 2s, 4s, 8s
                print(f"[summarize] attempt {attempt}/{retries} failed: {e}; retrying in {wait}s")
                time.sleep(wait)
            else:
                print(f"[summarize] attempt {attempt}/{retries} failed: {e}")
    raise last_error


def _trim_partial(text, finish_reason, label):
    """If the output hit the token cap, drop the item that was cut off mid-way."""
    if finish_reason != "length":
        return text.strip()
    cut = max(text.rfind("\n- **"), text.rfind("\n### "))
    print(f"[summarize] WARNING: {label} hit the output cap; dropping the unfinished last item.")
    return (text[:cut] if cut > 0 else text).strip()


def split_sections(markdown):
    """Split a digest body at its '## ' headings ('### 今日观察' stays with the last one)."""
    return [s.strip() for s in re.split(r"(?m)^(?=## )", markdown) if s.strip()]


def translate_digest(zh_text):
    """Translate a Chinese digest body to English, one section per call.

    A section that fails to translate is left out rather than failing the whole
    run; returns None only when nothing could be translated."""
    parts = []
    for section in split_sections(zh_text):
        try:
            text, reason = _chat(TRANSLATE_PROMPT, section, temperature=0.3)
        except Exception as e:  # network / API error on one section
            print(f"[summarize] WARNING: translating a section failed ({e}); skipping it.")
            continue
        parts.append(_trim_partial(text, reason, "English translation"))
    return "\n\n".join(parts) if parts else None


def format_raw_content(data):
    """Format fetched data into a text block for the AI."""
    sections = []

    if data.get("news"):
        sections.append("=== 新闻资讯 ===")
        for item in data["news"]:
            sections.append(
                f"[{item['source']}] {item['title']}\n"
                f"URL: {item['url']}\n"
                f"Published: {item.get('published') or 'unknown'}\n"
                f"Importance hint: {item.get('importance_hint', 3)}/5\n"
                f"{item['summary']}\n"
            )

    if data.get("papers"):
        sections.append("=== 学术论文 ===")
        for item in data["papers"]:
            sections.append(
                f"[{item['source']}] {item['title']}\n"
                f"URL: {item['url']}\n"
                f"Published: {item.get('published') or 'unknown'}\n"
                f"Importance hint: {item.get('importance_hint', 3)}/5\n"
                f"{item['summary']}\n"
            )

    if data.get("projects"):
        sections.append("=== 开源项目 ===")
        for item in data["projects"]:
            sections.append(
                f"[{item['source']}] {item['title']}\n"
                f"URL: {item['url']}\n"
                f"Importance hint: {item.get('importance_hint', 3)}/5\n"
                f"{item['summary']}\n"
            )

    return "\n".join(sections)


def _wrap(text, date_str, model, title):
    return f"""# {title} - {date_str}

{text}

---
*Generated by AI Daily Digest using {model}*
"""


def summarize(data, date_str):
    """Generate daily digest via OpenAI-compatible API (DeepSeek by default).

    Returns (zh_markdown, en_markdown). en_markdown is None if the English
    translation failed entirely.
    """
    model = os.environ.get("API_MODEL", "deepseek-chat")

    raw_content = format_raw_content(data)
    if not raw_content.strip():
        return (
            f"# AI Daily Digest - {date_str}\n\n> No content fetched today.\n",
            None,
        )

    user_prompt = f"""今天是 {date_str}。

以下是今天收集到的 AI 领域原始资讯，请整理成每日简报。
请优先选择重要性高、来源可靠、对 AI builder 有实际参考价值的内容：

{raw_content}"""

    print(f"Calling {model} for the Chinese digest...")
    zh_text, reason = _chat(SYSTEM_PROMPT, user_prompt)
    zh_text = _trim_partial(zh_text, reason, "Chinese digest")

    print("Translating to English, one section at a time...")
    en_text = translate_digest(zh_text)
    if not en_text:
        print("[summarize] WARNING: English translation failed; zh only.")

    zh_md = _wrap(zh_text, date_str, model, "AI Daily Digest")
    en_md = _wrap(en_text, date_str, model, "AI Daily Digest") if en_text else None
    return zh_md, en_md
