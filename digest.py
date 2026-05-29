import argparse
import io
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional

# Принудительно UTF-8 на stdout/stderr (нужно для Windows-консоли)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import feedparser
import requests
from dotenv import load_dotenv

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - optional dependency
    OpenAI = None


DEFAULT_SOURCES_FILE = os.path.join(os.path.dirname(__file__), "sources.json")
DEFAULT_RSSHUB_BASE = "https://rsshub.app"

# Резервные публичные RSShub-инстансы (перебираются при 403/ошибке)
RSSHUB_FALLBACKS = [
    "https://rsshub.rssforever.com",
    "https://rsshub.fly.dev",
    "https://rss.shab.fun",
]

# Специализированный сервис RSS для Telegram-каналов (работает без RSShub)
TG_RSS_TEMPLATE = "https://tg.i-c-a.su/rss/{channel}"

load_dotenv()


# ---------------------------------------------------------------------------
# Загрузка источников
# ---------------------------------------------------------------------------

def load_sources(path: str) -> Dict[str, List[Dict[str, str]]]:
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    return {
        "rss": data.get("rss", []),
        "telegram": data.get("telegram", []),
    }


def _rsshub_url(base: str, channel: str) -> str:
    token = os.getenv("RSSHUB_TOKEN")
    url = f"{base.rstrip('/')}/telegram/channel/{channel.lstrip('@')}"
    if token:
        url = f"{url}?key={token}"
    return url


def fetch_telegram_rss(channel: str) -> List[Dict[str, str]]:
    """Пробует несколько источников RSS для Telegram-канала по очереди."""
    channel = channel.lstrip("@")

    # 1. Если в .env задан свой RSShub — используем только его
    custom_base = os.getenv("RSSHUB_BASE")
    if custom_base and custom_base != DEFAULT_RSSHUB_BASE:
        return fetch_feed(_rsshub_url(custom_base, channel))

    candidates: List[str] = []

    # 2. Собственный GitHub Pages-фид (TG_FEED_BASE) — самый надёжный приоритет
    tg_feed_base = os.getenv("TG_FEED_BASE", "").rstrip("/")
    if tg_feed_base:
        candidates.append(f"{tg_feed_base}/{channel}.xml")

    # 3. Специализированный Telegram-RSS сервис
    candidates.append(TG_RSS_TEMPLATE.format(channel=channel))

    # 4. Публичные RSShub-инстансы как запасные варианты
    for base in [DEFAULT_RSSHUB_BASE] + RSSHUB_FALLBACKS:
        candidates.append(_rsshub_url(base, channel))

    last_exc: Exception = RuntimeError("Нет кандидатов")
    for url in candidates:
        try:
            return fetch_feed(url)
        except Exception as exc:
            last_exc = exc
            continue
    raise last_exc


# ---------------------------------------------------------------------------
# Получение ленты
# ---------------------------------------------------------------------------

def fetch_feed(url: str) -> List[Dict[str, str]]:
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; rss-digest/1.0; +https://example.com)"
    }
    response = requests.get(url, timeout=20, headers=headers)
    response.raise_for_status()
    parsed = feedparser.parse(response.text)
    items: List[Dict[str, str]] = []
    for entry in parsed.entries:
        if entry.get("content"):
            content = entry.content[0].get("value", "")
        else:
            content = entry.get("summary", "") or entry.get("description", "")
        published = entry.get("published", "") or entry.get("updated", "")
        items.append(
            {
                "title": entry.get("title", "").strip(),
                "content": content.strip(),
                "link": entry.get("link", "").strip(),
                "published": published.strip(),
            }
        )
    return items


def slice_items(items: List[Dict[str, str]], limit: int = 8) -> List[Dict[str, str]]:
    return items[:limit]


# ---------------------------------------------------------------------------
# ИИ-суммаризация
# ---------------------------------------------------------------------------

def openai_client() -> Optional["OpenAI"]:
    if OpenAI is None:
        return None
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("API_KEY")
    if not api_key:
        return None
    base_url = os.getenv("OPENAI_BASE_URL") or os.getenv("URL_MODEL")
    if base_url:
        return OpenAI(api_key=api_key, base_url=base_url)
    return OpenAI(api_key=api_key)


def summarize_with_llm(
    client: "OpenAI",
    label: str,
    items: List[Dict[str, str]],
    model: str,
) -> str:
    max_chars = int(os.getenv("MAX_INPUT_CHARS", "12000"))
    prompt_items = []
    used_chars = 0
    for idx, item in enumerate(items, start=1):
        published = item["published"]
        if published:
            try:
                published = datetime.fromisoformat(published).strftime("%Y-%m-%d")
            except Exception:
                pass
        block = (
            f"[{idx}] {published}\n"
            f"Заголовок: {item['title']}\n"
            f"Текст: {item['content']}\n"
            f"Ссылка: {item['link']}"
        )
        remaining = max_chars - used_chars
        if remaining <= 0:
            break
        if len(block) > remaining:
            block = block[:remaining]
        prompt_items.append(block)
        used_chars += len(block)

    prompt = (
        f"Суммаризируй последние новости источника \"{label}\".\n\n"
        "Новости:\n"
        + "\n\n".join(prompt_items)
        + "\n\nНапиши 3-4 предложения о главных темах. Не добавляй ссылки в текст."
    )
    system_message = (
        "Ты — редактор новостного дайджеста. Пишешь кратко, по делу, только на русском языке. "
        "Никогда не придумываешь факты — опираешься только на предоставленные новости. "
        "Без Markdown и без списков."
    )
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content.strip()


def simple_summary(label: str, items: List[Dict[str, str]]) -> str:
    if not items:
        return f"Источник {label}: новых материалов нет."
    titles = [item["title"] for item in items if item["title"]]
    if not titles:
        return f"Источник {label}: новые материалы доступны, но без заголовков."
    joined = "; ".join(titles[:3])
    return f"Основные темы: {joined}."


def summarize_source(label: str, items: List[Dict[str, str]]) -> str:
    if not items:
        return simple_summary(label, items)
    client = openai_client()
    if not client:
        print("  [!] API недоступен — используется простой режим", file=sys.stderr)
        return simple_summary(label, items)
    model = os.getenv("OPENAI_MODEL") or os.getenv("MODEL") or "gpt-4o-mini"
    return summarize_with_llm(client, label, items, model)


# ---------------------------------------------------------------------------
# Сбор и форматирование
# ---------------------------------------------------------------------------

def collect_sources(
    sources: Dict[str, List[Dict[str, str]]], limit: int, verbose: bool = False
) -> List[Dict]:
    all_sources = []
    for entry in sources.get("rss", []):
        all_sources.append(
            {
                "label": entry.get("label", entry.get("rss", "rss")),
                "rss": entry["rss"],
                "channel": None,
                "type": "rss",
            }
        )
    for entry in sources.get("telegram", []):
        channel = entry.get("channel", "").lstrip("@")
        all_sources.append(
            {
                "label": entry.get("label", channel or "telegram"),
                "rss": entry.get("rss"),  # None если не задан явно
                "channel": channel,
                "type": "telegram",
            }
        )

    results = []
    total = len(all_sources)
    for i, source in enumerate(all_sources, start=1):
        if verbose:
            print(f"[{i}/{total}] Обрабатываю: {source['label']} ...", file=sys.stderr)
        error_message = None
        items = []
        try:
            if source["type"] == "telegram" and not source["rss"]:
                items = fetch_telegram_rss(source["channel"])
            else:
                items = fetch_feed(source["rss"])
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response else "unknown"
            error_message = f"Ошибка получения ленты (HTTP {status})."
            print(f"  [!] {source['label']}: {exc}", file=sys.stderr)
        except Exception as exc:
            error_message = f"Ошибка: {exc}"
            print(f"  [!] {source['label']}: {exc}", file=sys.stderr)

        items = slice_items(items, limit=limit)
        summary = error_message or summarize_source(source["label"], items)
        top_links = [
            {"title": item["title"], "url": item["link"]}
            for item in items[:5]
            if item["link"]
        ]
        results.append(
            {
                "label": source["label"],
                "type": source["type"],
                "summary": summary,
                "links": top_links,
                "error": bool(error_message),
            }
        )
    return results


def format_text(results: List[Dict]) -> str:
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    sep = "─" * 60
    parts = [f"НОВОСТНОЙ ДАЙДЖЕСТ  {now}", sep]

    for item in results:
        status = "[ОШИБКА]" if item["error"] else ""
        parts.append(f"\n▶ {item['label']}  {status}".rstrip())
        parts.append(item["summary"])
        if item["links"]:
            parts.append("Источники:")
            for link in item["links"]:
                title = link["title"] or link["url"]
                parts.append(f"  • {title}")
                parts.append(f"    {link['url']}")

    parts.append(f"\n{sep}")
    parts.append(f"Конец дайджеста.")
    return "\n".join(parts)


def format_json(results: List[Dict]) -> str:
    output = {
        "generated_at": datetime.now().isoformat(),
        "sources": results,
    }
    return json.dumps(output, ensure_ascii=False, indent=2)


def format_html(results: List[Dict]) -> str:
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    rows = []
    for item in results:
        status_cls = ' class="error"' if item["error"] else ""
        links_html = ""
        if item["links"]:
            items_html = "".join(
                f'<li><a href="{l["url"]}" target="_blank">{l["title"] or l["url"]}</a></li>'
                for l in item["links"]
            )
            links_html = f"<ul>{items_html}</ul>"
        rows.append(
            f'<section{status_cls}>'
            f"<h2>{item['label']}</h2>"
            f"<p>{item['summary']}</p>"
            f"{links_html}"
            f"</section>"
        )
    body = "\n".join(rows)
    return (
        "<!DOCTYPE html><html lang='ru'><head>"
        "<meta charset='UTF-8'>"
        f"<title>Дайджест {now}</title>"
        "<style>"
        "body{font-family:sans-serif;max-width:860px;margin:2em auto;line-height:1.6}"
        "h1{border-bottom:2px solid #333;padding-bottom:.3em}"
        "section{margin:1.5em 0;padding:1em;border-left:4px solid #0af}"
        "section.error{border-color:#f44}"
        "h2{margin:0 0 .5em}"
        "ul{padding-left:1.2em}li{margin:.2em 0}"
        "a{color:#0066cc}"
        "</style>"
        "</head><body>"
        f"<h1>Новостной дайджест &mdash; {now}</h1>"
        f"{body}"
        "</body></html>"
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="RSS-дайджест с суммаризацией через ИИ"
    )
    parser.add_argument(
        "--sources",
        default=os.getenv("SOURCES_FILE", DEFAULT_SOURCES_FILE),
        help="Путь к файлу sources.json",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=int(os.getenv("ITEM_LIMIT", "8")),
        help="Максимум новостей на источник (по умолчанию 8)",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json", "html"],
        default="text",
        help="Формат вывода: text | json | html (по умолчанию text)",
    )
    parser.add_argument(
        "--output",
        metavar="FILE",
        help="Сохранить результат в файл (по умолчанию вывод в консоль)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Показывать прогресс обработки",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not os.path.exists(args.sources):
        print(f"Файл источников не найден: {args.sources}", file=sys.stderr)
        return 1

    sources = load_sources(args.sources)
    results = collect_sources(sources, limit=args.limit, verbose=args.verbose)

    if args.format == "json":
        digest = format_json(results)
    elif args.format == "html":
        digest = format_html(results)
    else:
        digest = format_text(results)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(digest)
        print(f"Дайджест сохранён: {args.output}", file=sys.stderr)
    else:
        print(digest)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
