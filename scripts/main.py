"""
AI Daily Digest - Main entry point.
Fetches AI news from multiple sources, summarizes with Gemini, and saves as markdown.
"""

import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

from sources import fetch_all
from summarize import summarize


def main():
    # Use Beijing time for date
    beijing_tz = timezone(timedelta(hours=8))
    today = datetime.now(beijing_tz)
    date_str = today.strftime("%Y-%m-%d")

    print(f"=== AI Daily Digest for {date_str} ===\n")

    # Step 1: Fetch data from all sources
    print("[Step 1] Fetching data from sources...")
    data = fetch_all()

    total = sum(len(v) for v in data.values())
    print(f"\nTotal items fetched: {total}")

    if total == 0:
        print("No items fetched. Exiting.")
        sys.exit(0)

    # Step 2: AI summarization
    print("\n[Step 2] Generating AI summary...")
    markdown = summarize(data, date_str)

    # Step 3: Save to file
    output_dir = Path(__file__).parent.parent / "daily"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"{date_str}.md"

    output_file.write_text(markdown, encoding="utf-8")
    print(f"\n[Step 3] Saved to {output_file}")
    print("Done!")


if __name__ == "__main__":
    main()
