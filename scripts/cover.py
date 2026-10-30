"""Daily social cover image (1080×1440) for 小红书 / 微信 posts.

The cover *is* the content: readers skim the five headlines straight from the
feed thumbnail. It reuses the digest's own one-line headline and star ratings,
so publishing is copy-image + copy-headline, with nothing retyped.

Rendered with headless Chrome — already present on GitHub's ubuntu runners and
on any Mac with Chrome installed. If no browser is found the daily run simply
skips the cover instead of failing.
"""

import base64
import math
import shutil
import subprocess
import tempfile
from pathlib import Path

from brandmark import logo_svg

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
]

# CJK stacks differ between macOS and CI; list both so either renders.
FONT_STACK = ('"PingFang SC","Noto Sans CJK SC","Noto Sans SC",'
              '"Hiragino Sans GB","Heiti SC",sans-serif')

NUM_COLORS = ["#ff2442", "#f97316", "#7c3aed", "#2440b8", "#0ea5e9"]

COVER_W, COVER_H = 1080, 1440


def find_chrome() -> str | None:
    for candidate in CHROME_CANDIDATES:
        if candidate.startswith("/"):
            if Path(candidate).exists():
                return candidate
        else:
            found = shutil.which(candidate)
            if found:
                return found
    return None


def render_html(html: str, out_path: Path,
                width: int = COVER_W, height: int = COVER_H) -> bool:
    """Screenshot an HTML string to PNG. False if no browser is available."""
    chrome = find_chrome()
    if not chrome:
        print("[cover] No Chrome/Chromium found; skipping image render.")
        return False

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "page.html"
        page.write_text(html, encoding="utf-8")
        cmd = [
            chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
            "--disable-dev-shm-usage", "--force-device-scale-factor=1",
            f"--window-size={width},{height}",
            f"--screenshot={out_path}",
            page.as_uri(),
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=60)
        except subprocess.TimeoutExpired:
            print("[cover] Browser render timed out; skipping image.")
            return False

    if not out_path.exists():
        print(f"[cover] Render failed: {result.stderr.decode()[:300]}")
        return False
    return True


def _logo_data_uri() -> str:
    svg = logo_svg("dark").encode("utf-8")
    return "data:image/svg+xml;base64," + base64.b64encode(svg).decode()


def _headline_size(headline: str) -> int:
    """Long headlines step down a size so the layout never overflows."""
    n = len(headline)
    if n <= 20:
        return 88
    if n <= 28:
        return 76
    return 64


def top_items(digest: dict, limit: int = 5) -> list:
    """The day's most important stories, most important first."""
    items = [i for cat in digest["categories"] for i in cat["items"]]
    items.sort(key=lambda x: -x["star_count"])
    return items[:limit]


# Layout constants in the cover's own pixels, measured off a real render and
# kept in sync with the CSS below.
_CARD_H = {1: 108, 2: 152}   # rendered card height by title line count
_CARD_GAP = 16
_CHARS_PER_LINE = 22         # full-width chars that fit one title line
# Everything above the card list: page padding, the date row, and the sub row.
_LIST_TOP = 64 + 68 + 44 + 108
# Everything below it: the footer and the bottom page padding, plus slack.
_LIST_BOTTOM = 88 + 62 + 10


def _title_lines(title: str) -> int:
    """How many lines a title wraps to (CJK is double-width, Latin single)."""
    weight = sum(1 if ord(c) > 0x2E80 else 0.5 for c in title)
    return max(1, min(2, math.ceil(weight / _CHARS_PER_LINE)))


def fit_items(items: list, headline: str, minimum: int = 3) -> list:
    """Drop trailing stories until the cards actually fit above the footer.

    Five long headlines overflow a 1440px cover; rather than clipping a card
    mid-sentence, the cover shows fewer, complete ones.
    """
    headline_h = _title_lines_for_headline(headline) * int(
        _headline_size(headline) * 1.24)
    available = COVER_H - _LIST_TOP - _LIST_BOTTOM - headline_h

    kept = []
    used = 0
    for item in items:
        height = _CARD_H[_title_lines(item["title"])]
        gap = _CARD_GAP if kept else 0
        if kept and used + gap + height > available and len(kept) >= minimum:
            break
        kept.append(item)
        used += gap + height
    return kept


def _title_lines_for_headline(headline: str) -> int:
    size = _headline_size(headline)
    chars_per_line = (COVER_W - 124) / size
    weight = sum(1 if ord(c) > 0x2E80 else 0.5 for c in headline)
    return max(1, math.ceil(weight / chars_per_line))


def build_cover_html(date_str: str, weekday: str, headline: str,
                     items: list, issue_no: int, source_count: int = 12) -> str:
    rows = ""
    for i, item in enumerate(items):
        color = NUM_COLORS[i % len(NUM_COLORS)]
        title = (item["title"].replace("&", "&amp;")
                 .replace("<", "&lt;").replace(">", "&gt;"))
        rows += (f'<li><div class="num" style="background:{color}">{i + 1}</div>'
                 f'<div class="t">{title}</div></li>')

    pretty_date = date_str.replace("-", ".")
    return f"""<!DOCTYPE html>
<html lang="zh-Hans"><head><meta charset="UTF-8"><style>
  html,body{{margin:0;padding:0}}
  body{{width:{COVER_W}px;height:{COVER_H}px;overflow:hidden;
       font-family:{FONT_STACK};background:#FFFCF6;position:relative}}
  .grid{{position:absolute;inset:0;
        background-image:radial-gradient(#1a1f3d12 1.6px,transparent 1.6px);
        background-size:26px 26px}}
  .blob{{position:absolute;width:620px;height:620px;right:-210px;top:-230px;
        border-radius:50%;
        background:radial-gradient(circle at 30% 30%,#7c3aed26,#2440b800 70%)}}
  .wrap{{position:relative;padding:64px 62px;height:100%;box-sizing:border-box;
        display:flex;flex-direction:column}}
  .top{{display:flex;align-items:center;justify-content:space-between;
       margin-bottom:44px}}
  .pill{{display:flex;align-items:center;gap:12px;
        background:linear-gradient(135deg,#2440b8,#7c3aed);
        color:#fff;font-size:30px;font-weight:600;padding:12px 26px;
        border-radius:999px;letter-spacing:1px}}
  .date{{font-size:29px;color:#5b6478;font-weight:500;letter-spacing:.5px}}
  h1{{font-size:{_headline_size(headline)}px;line-height:1.24;margin:0;
     color:#0d1220;font-weight:700;letter-spacing:-1px;
     background:linear-gradient(180deg,transparent 64%,#fbbf2466 64%);
     display:inline;box-decoration-break:clone;
     -webkit-box-decoration-break:clone;padding:0 4px}}
  .sub{{display:flex;align-items:center;gap:14px;margin:30px 0 30px}}
  .tag{{background:#ff2442;color:#fff;font-size:27px;font-weight:600;
       padding:8px 18px;border-radius:10px;white-space:nowrap}}
  .sub span{{font-size:29px;color:#5b6478}}
  ol{{list-style:none;margin:0;padding:0;flex:1;overflow:hidden;
     display:flex;flex-direction:column;justify-content:center;gap:16px}}
  li{{display:flex;align-items:flex-start;gap:20px;background:#fff;
     border:2px solid #eceef6;border-radius:20px;padding:22px 26px;
     box-shadow:0 6px 18px #1a1f3d0a}}
  .num{{flex:none;width:52px;height:52px;border-radius:14px;color:#fff;
       font-size:29px;font-weight:700;display:flex;align-items:center;
       justify-content:center}}
  .t{{font-size:36px;line-height:1.42;color:#141a2b;font-weight:600;
     padding-top:5px;display:-webkit-box;-webkit-line-clamp:2;
     -webkit-box-orient:vertical;overflow:hidden}}
  .foot{{display:flex;align-items:center;justify-content:space-between;
        padding-top:10px}}
  .brand{{display:flex;align-items:center;gap:18px}}
  .brand img{{width:78px;height:78px;border-radius:22px}}
  .brand div{{font-size:28px;color:#3a4358;line-height:1.4}}
  .brand b{{display:block;font-size:31px;color:#141a2b}}
  .cta{{font-size:30px;font-weight:600;color:#ff2442;background:#ff24421a;
       padding:14px 24px;border-radius:14px}}
</style></head><body>
<div class="grid"></div><div class="blob"></div>
<div class="wrap">
  <div class="top">
    <div class="pill">⚡ AI 日报 · 第 {issue_no} 期</div>
    <div class="date">{pretty_date} {weekday}</div>
  </div>
  <div><h1>{headline}</h1></div>
  <div class="sub">
    <div class="tag">今日 {len(items)} 件大事</div>
    <span>全网 {source_count} 个信息源 · 3 分钟看完</span>
  </div>
  <ol>{rows}</ol>
  <div class="foot">
    <div class="brand">
      <img src="{_logo_data_uri()}">
      <div><b>AI Daily Digest</b>每天早 8 点自动更新 · 已连更 {issue_no} 期</div>
    </div>
    <div class="cta">收藏 ↗</div>
  </div>
</div></body></html>"""


def generate_cover(root: Path, date_str: str, digest: dict,
                   issue_no: int) -> Path | None:
    """Render docs/covers/{date}.png. Returns the path, or None if skipped."""
    from generate_site import digest_headline, weekday_of

    headline = digest_headline(digest)
    candidates = top_items(digest, limit=6)
    # A fallback headline is just the top story's title, so showing that story
    # again as card #1 would print the same sentence twice.
    if not digest.get("headline"):
        candidates = [i for i in candidates if i["title"] != headline]

    items = fit_items(candidates, headline)
    if not items:
        print("[cover] No items for this date; skipping.")
        return None

    html = build_cover_html(
        date_str=date_str,
        weekday=weekday_of(date_str),
        headline=headline,
        items=items,
        issue_no=issue_no,
    )
    out = root / "docs" / "covers" / f"{date_str}.png"
    if not render_html(html, out):
        return None
    print(f"  Cover → {out.relative_to(root)}")
    return out


def prune_old_covers(covers_dir: Path, keep: int = 30) -> None:
    """Covers are ~250 KB each; keep a month of them in the repo."""
    if not covers_dir.exists():
        return
    files = sorted(covers_dir.glob("*.png"), reverse=True)
    for stale in files[keep:]:
        stale.unlink()
        print(f"  Pruned old cover: {stale.name}")
