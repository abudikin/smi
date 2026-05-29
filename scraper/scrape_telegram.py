"""
Скрапер открытых Telegram-каналов через t.me/s/.
Не требует Telegram-аккаунта или API-ключей.
Запускается в GitHub Actions (серверы за рубежом — t.me доступен).

Выход:
  dist/{channel}.xml  — RSS 2.0 лента
  dist/index.json     — список каналов и URL фидов
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator

CHANNELS_FILE = Path(__file__).parent / "channels.json"
DIST_DIR = Path(__file__).parent.parent / "dist"
TG_WEB_URL = "https://t.me/s/{channel}"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ru,en;q=0.9",
}

# Число постов, которые реально нужны (t.me/s/ отдаёт до ~20)
POST_LIMIT = 20
# Задержка между запросами к разным каналам (сек), чтобы не словить 429
REQUEST_DELAY = 2.0


def scrape_channel(channel: str) -> list[dict]:
    """
    Скачивает t.me/s/{channel} и извлекает посты.
    Возвращает список словарей с ключами: id, text, link, published.
    """
    url = TG_WEB_URL.format(channel=channel)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"  [!] {channel}: не удалось получить страницу: {exc}", file=sys.stderr)
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    posts = []

    for wrap in soup.select(".tgme_widget_message_wrap"):
        msg = wrap.select_one(".tgme_widget_message")
        if msg is None:
            continue

        # ---- ID и ссылка ----
        data_post = msg.get("data-post", "")
        if not data_post:
            continue
        post_id = data_post.split("/")[-1] if "/" in data_post else data_post
        link = f"https://t.me/{data_post}"

        # ---- Текст ----
        text_el = msg.select_one(".tgme_widget_message_text")
        text = text_el.get_text(separator="\n", strip=True) if text_el else ""

        # ---- Дата ----
        time_el = msg.select_one("time[datetime]")
        published_raw = time_el["datetime"] if time_el else ""
        try:
            published = datetime.fromisoformat(published_raw.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            published = datetime.now(timezone.utc)

        posts.append(
            {
                "id": post_id,
                "text": text,
                "link": link,
                "published": published,
            }
        )

    # Отдаём в хронологически обратном порядке (свежие первыми)
    posts.sort(key=lambda p: p["published"], reverse=True)
    return posts[:POST_LIMIT]


def build_rss(channel: str, label: str, posts: list[dict], feed_base_url: str) -> bytes:
    """
    Строит RSS 2.0 из списка постов.
    feed_base_url используется для ссылки на сам фид.
    """
    fg = FeedGenerator()
    fg.id(f"https://t.me/{channel}")
    fg.title(label)
    fg.link(href=f"https://t.me/{channel}", rel="alternate")
    fg.link(href=f"{feed_base_url}/{channel}.xml", rel="self")
    fg.language("ru")
    fg.description(f"Telegram-канал @{channel}")
    fg.lastBuildDate(datetime.now(timezone.utc))

    for post in posts:
        fe = fg.add_entry()
        fe.id(post["link"])
        title = (post["text"].splitlines()[0][:120] if post["text"] else post["link"])
        fe.title(title)
        fe.link(href=post["link"])
        fe.published(post["published"])
        fe.updated(post["published"])
        if post["text"]:
            fe.content(post["text"], type="text")

    return fg.rss_str(pretty=True)


def main() -> int:
    with open(CHANNELS_FILE, encoding="utf-8") as f:
        channels = json.load(f)

    feed_base_url = os.getenv("FEED_BASE_URL", "").rstrip("/")
    if not feed_base_url:
        # При локальном запуске используем заглушку
        feed_base_url = "http://localhost/feeds"

    DIST_DIR.mkdir(parents=True, exist_ok=True)

    index: list[dict] = []
    total = len(channels)

    for i, entry in enumerate(channels, start=1):
        channel = entry["channel"].lstrip("@")
        label = entry.get("label", channel)
        print(f"[{i}/{total}] {label} (@{channel}) ...", file=sys.stderr)

        posts = scrape_channel(channel)
        if not posts:
            print(f"  -> нет постов, пропускаем", file=sys.stderr)
        else:
            rss_bytes = build_rss(channel, label, posts, feed_base_url)
            out_path = DIST_DIR / f"{channel}.xml"
            out_path.write_bytes(rss_bytes)
            print(f"  -> {len(posts)} постов -> {out_path}", file=sys.stderr)

        index.append(
            {
                "channel": channel,
                "label": label,
                "feed": f"{feed_base_url}/{channel}.xml",
                "posts": len(posts),
            }
        )

        if i < total:
            time.sleep(REQUEST_DELAY)

    index_path = DIST_DIR / "index.json"
    index_path.write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nГотово. index.json -> {index_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
