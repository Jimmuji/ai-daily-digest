"""
AI Daily Digest - Main entry point.
Fetches AI news from multiple sources, summarizes with AI, and saves outputs.
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

from sources import (
    fetch_all,
    load_recent_seen_urls,
    drop_seen_items,
    record_published_urls,
)
from summarize import summarize
from generate_site import generate_site, parse_digest
from audio import generate_audio, prune_old_audio
from cover import generate_cover, prune_old_covers


def send_to_buttondown(subject: str, markdown: str) -> None:
    """Publish the digest as a Buttondown email (sends to all subscribers)."""
    api_key = os.environ.get("BUTTONDOWN_API_KEY")
    if not api_key:
        print("[Buttondown] BUTTONDOWN_API_KEY not set, skipping.")
        return

    resp = requests.post(
        "https://api.buttondown.email/v1/emails",
        headers={
            "Authorization": f"Token {api_key}",
            "X-Buttondown-Live-Dangerously": "true",
        },
        json={
            "subject": subject,
            "body": markdown,
            "status": "about_to_send",  # queues for immediate send
            "email_type": "public",    # visible in archive
        },
        timeout=30,
    )
    if resp.status_code in (200, 201):
        print(f"[Buttondown] Sent! Email id: {resp.json().get('id')}")
    else:
        print(f"[Buttondown] Failed {resp.status_code}: {resp.text[:200]}")


def main():
    # Use Beijing time for date
    beijing_tz = timezone(timedelta(hours=8))
    today = datetime.now(beijing_tz)
    date_str = today.strftime("%Y-%m-%d")

    print(f"=== AI Daily Digest for {date_str} ===\n")

    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(exist_ok=True)
    seen_file = data_dir / "seen_urls.json"

    # Step 1: Fetch data from all sources
    print("[Step 1] Fetching data from sources...")
    data = fetch_all()

    # Drop stories already published in recent digests (cross-day dedup)
    seen_urls = load_recent_seen_urls(seen_file, window_days=5)
    data, dropped = drop_seen_items(data, seen_urls)
    if dropped:
        print(f"Dropped {dropped} item(s) already published in the last 5 days.")

    total = sum(len(v) for v in data.values())
    print(f"\nTotal items after dedup: {total}")

    if total == 0:
        print("No items fetched. Exiting.")
        sys.exit(0)

    # Step 2: Save raw fetched data for traceability
    raw_file = data_dir / f"{date_str}.raw.json"
    raw_payload = {
        "date": date_str,
        "generated_at": today.isoformat(),
        "counts": {key: len(value) for key, value in data.items()},
        "items": data,
    }
    raw_file.write_text(
        json.dumps(raw_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n[Step 2] Saved raw data to {raw_file}")

    # Step 3: AI summarization (bilingual)
    print("\n[Step 3] Generating AI summary...")
    markdown, markdown_en = summarize(data, date_str)

    # Step 4: Save daily markdown (zh + en)
    output_dir = Path(__file__).parent.parent / "daily"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"{date_str}.md"

    output_file.write_text(markdown, encoding="utf-8")
    print(f"\n[Step 4] Saved to {output_file}")

    if markdown_en:
        output_file_en = output_dir / f"{date_str}.en.md"
        output_file_en.write_text(markdown_en, encoding="utf-8")
        print(f"          Saved English to {output_file_en}")
    else:
        print("          No English version generated.")

    # Remember the source links we published so they don't recur tomorrow.
    published = record_published_urls(seen_file, date_str, markdown, window_days=7)
    print(f"          Recorded {published} published URL(s) for cross-day dedup.")

    # Step 5: Synthesize voice broadcast (MP3 for commute listening)
    print("\n[Step 5] Generating voice broadcast...")
    audio_dir = Path(__file__).parent.parent / "docs" / "audio"
    try:
        generate_audio(markdown, date_str, audio_dir)
        prune_old_audio(audio_dir, keep=15)  # keep ~half a month of episodes
    except Exception as e:
        print(f"  Audio generation skipped: {e}")

    # Step 5.5: Social cover image (ready to post to 小红书 / 微信)
    print("\n[Step 5.5] Rendering social cover...")
    root = Path(__file__).parent.parent
    try:
        issue_no = len([f for f in output_dir.glob("*.md")
                        if not f.name.endswith(".en.md")])
        generate_cover(root, date_str, parse_digest(markdown), issue_no)
        prune_old_covers(root / "docs" / "covers", keep=30)
    except Exception as e:
        print(f"  Cover generation skipped: {e}")

    # Step 6: Rebuild static site (picks up today's audio + podcast feed)
    print("\n[Step 6] Rebuilding static site...")
    generate_site(root=Path(__file__).parent.parent)
    print("  Site rebuilt → docs/")

    # Step 7: Send to Buttondown subscribers
    print("\n[Step 7] Sending to Buttondown subscribers...")
    subject = f"AI Daily Digest · {date_str}"
    send_to_buttondown(subject, markdown)

    print("Done!")


if __name__ == "__main__":
    main()
