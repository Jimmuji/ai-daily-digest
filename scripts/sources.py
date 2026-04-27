"""
Data source fetchers - all free, no AI tokens needed.
Each function returns a list of dicts with stable fields for traceability.
"""

import html
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import feedparser
import requests


AI_KEYWORDS = [
    "ai", "ml", "llm", "gpt", "transformer", "neural", "deep-learning",
    "machine-learning", "nlp", "diffusion", "agent", "rag", "embedding",
    "model", "inference", "fine-tun", "lora", "vision", "multimodal",
    "chatbot", "langchain", "openai", "anthropic", "gemini", "claude",
]

HIGH_SIGNAL_KEYWORDS = [
    "release", "launch", "open source", "benchmark", "state-of-the-art",
    "sota", "reasoning", "inference", "agent", "multimodal", "model",
    "api", "eval", "safety", "chip", "funding", "acquisition",
    "发布", "开源", "融资", "收购", "基准", "推理", "模型", "智能体",
    "多模态", "安全", "芯片",
]

TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"}


def clean_text(value, max_chars=500):
    """Strip HTML and whitespace noise from source summaries."""
    text = html.unescape(value or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]


def normalize_url(url):
    """Normalize URLs so the same story is easier to dedupe."""
    if not url:
        return ""
    parts = urlsplit(url.strip())
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key.lower() not in TRACKING_PARAMS
    ]
    return urlunsplit((
        parts.scheme.lower(),
        parts.netloc.lower(),
        parts.path.rstrip("/"),
        urlencode(query, doseq=True),
        "",
    ))


def normalize_title(title):
    return re.sub(r"\W+", "", (title or "").lower())


def estimate_importance(category, title, summary, source):
    """Give the model a transparent first-pass signal without replacing editorial judgment."""
    text = f"{title} {summary} {source}".lower()
    score = 3

    if category in {"papers", "projects"}:
        score += 1
    if any(keyword in text for keyword in HIGH_SIGNAL_KEYWORDS):
        score += 1
    if any(name in text for name in ["openai", "anthropic", "google", "deepmind", "meta", "microsoft", "nvidia"]):
        score += 1

    return max(1, min(5, score))


def make_item(category, title, url, summary, source, published=None, metadata=None):
    cleaned_summary = clean_text(summary)
    return {
        "category": category,
        "title": clean_text(title, max_chars=220),
        "url": url or "",
        "normalized_url": normalize_url(url),
        "summary": cleaned_summary,
        "source": source,
        "published": published,
        "importance_hint": estimate_importance(category, title, cleaned_summary, source),
        "metadata": metadata or {},
    }


def dedupe_items(items):
    """Deduplicate by normalized URL first, then normalized title."""
    seen = {}
    url_index = {}
    title_index = {}

    for item in items:
        url_key = item.get("normalized_url")
        title_key = normalize_title(item.get("title"))
        key = url_index.get(url_key) or title_index.get(title_key)

        if not key:
            key = url_key or title_key
        if not key:
            continue

        previous = seen.get(key)
        if not previous:
            seen[key] = item
            if url_key:
                url_index[url_key] = key
            if title_key:
                title_index[title_key] = key
            continue

        if len(item.get("summary", "")) > len(previous.get("summary", "")):
            item["source"] = f"{previous['source']}, {item['source']}"
            item["importance_hint"] = max(previous["importance_hint"], item["importance_hint"])
            seen[key] = item
            if url_key:
                url_index[url_key] = key
            if title_key:
                title_index[title_key] = key
        else:
            previous["source"] = f"{previous['source']}, {item['source']}"
            previous["importance_hint"] = max(previous["importance_hint"], item["importance_hint"])

    return list(seen.values())


def fetch_huggingface_papers():
    """Fetch today's papers from HuggingFace Daily Papers API."""
    items = []
    try:
        resp = requests.get("https://huggingface.co/api/daily_papers", timeout=30)
        resp.raise_for_status()
        papers = resp.json()
        for p in papers[:20]:  # top 20
            paper = p.get("paper", {})
            paper_id = paper.get("id", "")
            items.append(make_item(
                category="papers",
                title=paper.get("title", ""),
                url=f"https://huggingface.co/papers/{paper_id}",
                summary=paper.get("summary", ""),
                source="HuggingFace Papers",
                published=paper.get("publishedAt") or paper.get("submittedOn"),
                metadata={"paper_id": paper_id},
            ))
    except Exception as e:
        print(f"[HuggingFace Papers] Error: {e}")
    return items


def fetch_github_trending():
    """Fetch trending repos from OSSInsight API (free, no auth)."""
    items = []
    try:
        resp = requests.get(
            "https://api.ossinsight.io/v1/trends/repos?period=past_24_hours",
            timeout=30,
        )
        resp.raise_for_status()
        rows = resp.json().get("data", {}).get("rows", [])
        # Filter for AI/ML related repos by keywords
        for repo in rows:
            desc = (repo.get("description") or "").lower()
            name = (repo.get("repo_name") or "").lower()
            lang = (repo.get("primary_language") or "").lower()
            text = f"{desc} {name} {lang}"
            if any(kw in text for kw in AI_KEYWORDS):
                repo_name = repo.get("repo_name", "")
                items.append(make_item(
                    category="projects",
                    title=f"{repo_name} ⭐{repo.get('stars', 0)}",
                    url=f"https://github.com/{repo_name}",
                    summary=repo.get("description", "") or "No description",
                    source="GitHub Trending",
                    metadata={
                        "stars": repo.get("stars", 0),
                        "language": repo.get("primary_language"),
                    },
                ))
        items = items[:15]  # cap at 15
    except Exception as e:
        print(f"[GitHub Trending] Error: {e}")
    return items


BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
}


def fetch_rss_feed(feed_url, source_name, max_items=10):
    """Generic RSS feed fetcher."""
    items = []
    try:
        resp = requests.get(feed_url, headers=BROWSER_HEADERS, timeout=20)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
        cutoff = datetime.now(timezone.utc) - timedelta(days=2)
        for entry in feed.entries[:max_items]:
            published = entry.get("published_parsed") or entry.get("updated_parsed")
            if published:
                entry_date = datetime(*published[:6], tzinfo=timezone.utc)
                if entry_date < cutoff:
                    continue
                published_at = entry_date.isoformat()
            else:
                published_at = None
            items.append(make_item(
                category="news",
                title=entry.get("title", ""),
                url=entry.get("link", ""),
                summary=entry.get("summary", ""),
                source=source_name,
                published=published_at,
                metadata={"feed_url": feed_url},
            ))
    except Exception as e:
        print(f"  [{source_name}] Error: {e}")
    return items


def fetch_hacker_news():
    """Fetch top AI stories from Hacker News via Algolia API."""
    items = []
    try:
        from datetime import datetime, timezone, timedelta
        since = int((datetime.now(timezone.utc) - timedelta(days=1)).timestamp())
        url = (
            f"https://hn.algolia.com/api/v1/search"
            f"?query=AI+LLM+machine+learning"
            f"&tags=story"
            f"&numericFilters=created_at_i>{since},points>10"
            f"&hitsPerPage=30"
        )
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        hits = resp.json().get("hits", [])

        for hit in hits:
            title = hit.get("title", "")
            # Filter for AI-relevant titles
            if not any(kw in title.lower() for kw in AI_KEYWORDS):
                continue
            items.append(make_item(
                category="news",
                title=title,
                url=hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
                summary=f"HN points: {hit.get('points', 0)}, comments: {hit.get('num_comments', 0)}",
                source="Hacker News",
                published=hit.get("created_at"),
            ))
        items = items[:15]
    except Exception as e:
        print(f"  [Hacker News] Error: {e}")
    return items


# RSS sources - all free, no auth needed
RSS_SOURCES = [
    # Chinese sources
    ("https://rsshub.rssforever.com/36kr/search/articles/ai", "36Kr AI"),
    ("https://rsshub.rssforever.com/sspai/tag/AI", "SSPAI AI"),
    # English sources
    ("https://venturebeat.com/category/ai/feed/",                          "VentureBeat AI"),
    ("https://techcrunch.com/category/artificial-intelligence/feed/",      "TechCrunch AI"),
    ("https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",  "The Verge AI"),
]


def fetch_all():
    """Fetch from all sources, return categorized data."""
    print("Fetching HuggingFace Papers...")
    papers = fetch_huggingface_papers()
    print(f"  Got {len(papers)} papers")

    print("Fetching GitHub Trending...")
    projects = fetch_github_trending()
    print(f"  Got {len(projects)} projects")

    print("Fetching Hacker News...")
    hn_items = fetch_hacker_news()
    print(f"  Got {len(hn_items)} items")

    print("Fetching RSS feeds...")
    news = list(hn_items)
    for url, name in RSS_SOURCES:
        feed_items = fetch_rss_feed(url, name)
        print(f"  [{name}] Got {len(feed_items)} items")
        news.extend(feed_items)

    data = {
        "papers": dedupe_items(papers),
        "projects": dedupe_items(projects),
        "news": dedupe_items(news),
    }

    deduped_total = sum(len(v) for v in data.values())
    raw_total = len(papers) + len(projects) + len(news)
    print(f"Deduped {raw_total} raw items to {deduped_total} unique items")
    return data
