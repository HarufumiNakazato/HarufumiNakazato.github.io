#!/usr/bin/env python3
"""
量子株自動投稿スクリプト
Researches quantum computing stock news and posts to X (Twitter) daily.
"""

import os
import json
import hashlib
import feedparser
import anthropic
import tweepy
import yfinance as yf
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")

# Quantum computing stocks to track
QUANTUM_STOCKS = {
    "IONQ": "IonQ",
    "RGTI": "Rigetti Computing",
    "QBTS": "D-Wave Quantum",
    "QUBT": "Quantum Computing Inc",
    "QTUM": "Defiance Quantum ETF",
    "IBM": "IBM (量子部門)",
}

# RSS feeds for quantum computing & stock news
RSS_FEEDS = [
    "https://finance.yahoo.com/rss/headline?s=IONQ",
    "https://finance.yahoo.com/rss/headline?s=RGTI",
    "https://finance.yahoo.com/rss/headline?s=QBTS",
    "https://finance.yahoo.com/rss/headline?s=QUBT",
    "https://quantumcomputingreport.com/feed/",
    "https://thequantuminsider.com/feed/",
    "https://feeds.feedburner.com/QuantumDaily",
]

POSTED_HASHES_FILE = Path(__file__).parent / "posted_hashes.json"
MAX_TWEET_LENGTH = 280


def load_posted_hashes() -> set:
    if POSTED_HASHES_FILE.exists():
        with open(POSTED_HASHES_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return set(data.get("hashes", []))
    return set()


def save_posted_hashes(hashes: set):
    # Keep only last 200 hashes to prevent unbounded growth
    hashes_list = list(hashes)[-200:]
    data = {
        "hashes": hashes_list,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(POSTED_HASHES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def fetch_stock_prices() -> dict:
    prices = {}
    for ticker, name in QUANTUM_STOCKS.items():
        try:
            stock = yf.Ticker(ticker)
            info = stock.fast_info
            current = info.last_price
            prev_close = info.previous_close
            if current and prev_close:
                change_pct = ((current - prev_close) / prev_close) * 100
                prices[ticker] = {
                    "name": name,
                    "price": current,
                    "change_pct": change_pct,
                }
                print(f"  {ticker}: ${current:.2f} ({change_pct:+.1f}%)")
        except Exception as e:
            print(f"  Warning: could not fetch {ticker}: {e}")
    return prices


def fetch_recent_news(hours: int = 24) -> list[dict]:
    news_items = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    posted_hashes = load_posted_hashes()

    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url, request_headers={"User-Agent": "Mozilla/5.0"})
            for entry in feed.entries[:5]:
                title = entry.get("title", "").strip()
                link = entry.get("link", "")
                summary = entry.get("summary", "").strip()

                if not title:
                    continue

                content_hash = hashlib.md5(f"{title}{link}".encode()).hexdigest()
                if content_hash in posted_hashes:
                    continue

                published = entry.get("published_parsed")
                if published:
                    try:
                        pub_dt = datetime(*published[:6], tzinfo=timezone.utc)
                        if pub_dt < cutoff:
                            continue
                    except Exception:
                        pass

                news_items.append({
                    "title": title,
                    "link": link,
                    "summary": summary[:300],
                    "hash": content_hash,
                })
        except Exception as e:
            print(f"  Warning: could not fetch feed {feed_url}: {e}")

    # Deduplicate by hash, return up to 8 items
    seen = set()
    unique = []
    for item in news_items:
        if item["hash"] not in seen:
            seen.add(item["hash"])
            unique.append(item)
    return unique[:8]


def build_tweet_with_claude(stock_prices: dict, news_items: list) -> str:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    today_jst = datetime.now(JST).strftime("%Y/%m/%d")

    prices_lines = []
    for ticker, data in stock_prices.items():
        arrow = "▲" if data["change_pct"] >= 0 else "▼"
        prices_lines.append(
            f"  {ticker}: ${data['price']:.2f} {arrow}{abs(data['change_pct']):.1f}%"
        )
    prices_text = "\n".join(prices_lines) if prices_lines else "  (取得できませんでした)"

    news_lines = [f"  ・{item['title']}" for item in news_items[:5]]
    news_text = "\n".join(news_lines) if news_lines else "  (本日の新着ニュースなし)"

    prompt = f"""あなたは量子コンピュータ・量子株の情報を発信するSNSアカウントの担当者です。
以下のデータをもとに、X(Twitter)に投稿する日本語ツイートを1つ作成してください。

■ 日付: {today_jst}（米国市場）

■ 量子株 株価
{prices_text}

■ 最新ニュース
{news_text}

【ツイート作成ルール】
- 日本語で {MAX_TWEET_LENGTH} 文字以内（必ず守ること）
- 冒頭に適切な絵文字を使い視認性を高める
- 株価とニュースのポイントを簡潔にまとめる
- 末尾にハッシュタグ: #量子株 #量子コンピュータ
- 投資助言ではなく「情報提供」として書く
- 数値は正確に記載する（株価など）

ツイート本文のみ出力してください（前後の説明文は不要）。"""

    message = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


def truncate_tweet(text: str, max_len: int = MAX_TWEET_LENGTH) -> str:
    """Ensure tweet is within character limit (Twitter counts in Unicode code points)."""
    if len(text) <= max_len:
        return text
    # Truncate and add ellipsis, keeping hashtags if possible
    return text[: max_len - 1] + "…"


def post_to_x(tweet_text: str) -> str:
    client = tweepy.Client(
        consumer_key=os.environ["X_API_KEY"],
        consumer_secret=os.environ["X_API_SECRET"],
        access_token=os.environ["X_ACCESS_TOKEN"],
        access_token_secret=os.environ["X_ACCESS_TOKEN_SECRET"],
    )
    response = client.create_tweet(text=tweet_text)
    tweet_id = response.data["id"]
    print(f"  Posted tweet ID: {tweet_id}")
    return tweet_id


def main():
    print(f"=== Quantum Stock Poster started at {datetime.now(timezone.utc).isoformat()} ===")

    # 1. Fetch stock prices
    print("\n[1] Fetching stock prices...")
    stock_prices = fetch_stock_prices()
    if not stock_prices:
        print("  Warning: no stock prices fetched.")

    # 2. Fetch recent news
    print("\n[2] Fetching recent news (last 24h)...")
    news_items = fetch_recent_news(hours=24)
    print(f"  Found {len(news_items)} new item(s).")

    # 3. Generate tweet via Claude
    print("\n[3] Generating tweet with Claude...")
    tweet_text = build_tweet_with_claude(stock_prices, news_items)
    tweet_text = truncate_tweet(tweet_text)
    print(f"\n--- Tweet preview ({len(tweet_text)} chars) ---")
    print(tweet_text)
    print("---")

    dry_run = os.environ.get("DRY_RUN", "false").lower() == "true"

    # 4. Post to X (skip if dry run)
    if dry_run:
        print("\n[4] DRY RUN — skipping X post.")
        print("\n=== Done (dry run). ===")
        return

    print("\n[4] Posting to X...")
    tweet_id = post_to_x(tweet_text)

    # 5. Save hashes of posted news to avoid duplicates
    posted_hashes = load_posted_hashes()
    for item in news_items:
        posted_hashes.add(item["hash"])
    save_posted_hashes(posted_hashes)
    print(f"  Saved {len(news_items)} hash(es) to avoid future duplicates.")

    print(f"\n=== Done. Tweet ID: {tweet_id} ===")


if __name__ == "__main__":
    main()
