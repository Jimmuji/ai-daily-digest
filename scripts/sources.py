"""
Data source fetchers - all free, no AI tokens needed.
Each function returns a list of dicts: {title, url, summary, source}
"""

import requests
import feedparser
from datetime import datetime, timedelta, timezone


def fetch_huggingface_papers():
    """Fetch today's papers from HuggingFace Daily Papers API."""
    items = []
    try:
        resp = requests.get("https://huggingface.co/api/daily_papers", timeout=30)
        resp.raise_for_status()
        papers = resp.json()
        for p in papers[:20]:  # top 20
            paper = p.get("paper", {})
            items.append({
                "title": paper.get("title", ""),
                "url": f"https://huggingface.co/papers/{paper.get('id', '')}",
                "summary": paper.get("summary", "")[:500],
                "source": "HuggingFace Papers",
            })
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
        ai_keywords = [
            "ai", "ml", "llm", "gpt", "transformer", "neural", "deep-learning",
            "machine-learning", "nlp", "diffusion", "agent", "rag", "embedding",
            "model", "inference", "fine-tun", "lora", "vision", "multimodal",
            "chatbot", "langchain", "openai", "anthropic", "gemini", "claude",
        ]
        for repo in rows:
            desc = (repo.get("description") or "").lower()
            name = (repo.get("repo_name") or "").lower()
            lang = (repo.get("primary_language") or "").lower()
            text = f"{desc} {name} {lang}"
            if any(kw in text for kw in ai_keywords):
                repo_name = repo.get("repo_name", "")
                items.append({
                    "title": f"{repo_name} ⭐{repo.get('stars', 0)}",
                    "url": f"https://github.com/{repo_name}",
                    "summary": repo.get("description", "") or "No description",
                    "source": "GitHub Trending",
                })
        items = items[:15]  # cap at 15
    except Exception as e:
        print(f"[GitHub Trending] Error: {e}")
    return items


def fetch_rss_feed(feed_url, source_name, max_items=10):
    """Generic RSS feed fetcher."""
    items = []
    try:
        feed = feedparser.parse(feed_url)
        cutoff = datetime.now(timezone.utc) - timedelta(days=2)
        for entry in feed.entries[:max_items]:
            # Try to parse date
            published = entry.get("published_parsed") or entry.get("updated_parsed")
            if published:
                entry_date = datetime(*published[:6], tzinfo=timezone.utc)
                if entry_date < cutoff:
                    continue
            items.append({
                "title": entry.get("title", ""),
                "url": entry.get("link", ""),
                "summary": entry.get("summary", "")[:500],
                "source": source_name,
            })
    except Exception as e:
        print(f"[{source_name}] Error: {e}")
    return items


# RSS sources - all free, no auth needed
RSS_SOURCES = [
    # Chinese sources (via working RSSHub mirror)
    ("https://rsshub.rssforever.com/36kr/search/articles/ai", "36Kr AI"),
    ("https://rsshub.rssforever.com/sspai/tag/AI", "SSPAI AI"),
    # English sources
    ("https://techcrunch.com/category/artificial-intelligence/feed/", "TechCrunch AI"),
    ("https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "The Verge AI"),
]


def fetch_all():
    """Fetch from all sources, return categorized data."""
    print("Fetching HuggingFace Papers...")
    papers = fetch_huggingface_papers()
    print(f"  Got {len(papers)} papers")

    print("Fetching GitHub Trending...")
    projects = fetch_github_trending()
    print(f"  Got {len(projects)} projects")

    print("Fetching RSS feeds...")
    news = []
    for url, name in RSS_SOURCES:
        feed_items = fetch_rss_feed(url, name)
        print(f"  [{name}] Got {len(feed_items)} items")
        news.extend(feed_items)

    return {
        "papers": papers,
        "projects": projects,
        "news": news,
    }
