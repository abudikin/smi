import Parser from "rss-parser";

const DEFAULT_RSSHUB_BASE = "https://rsshub.app";
const RSSHUB_FALLBACKS = [
  "https://rsshub.rssforever.com",
  "https://rsshub.fly.dev",
  "https://rss.shab.fun",
];
const TG_RSS_TEMPLATE = "https://tg.i-c-a.su/rss/{channel}";

const parser = new Parser({
  timeout: 20000,
  headers: {
    "User-Agent": "Mozilla/5.0 (compatible; smi-admin/1.0)",
  },
});

export type RssItem = {
  title: string;
  link: string;
  published: string;
  content: string;
};

export type SourceInput = {
  type: "rss" | "telegram";
  rssUrl?: string | null;
  channel?: string | null;
};

const normalizeItem = (item: Parser.Item): RssItem => ({
  title: (item.title ?? "").trim(),
  link: (item.link ?? "").trim(),
  published: (item.isoDate ?? item.pubDate ?? "").trim(),
  content: (item.contentSnippet ?? item.content ?? "").trim(),
});

const rsshubUrl = (base: string, channel: string) =>
  `${base.replace(/\/$/, "")}/telegram/channel/${channel.replace(/^@/, "")}`;

const telegramCandidates = (channel: string) => {
  const normalized = channel.replace(/^@/, "");
  const customBase = process.env.RSSHUB_BASE;
  if (customBase && customBase !== DEFAULT_RSSHUB_BASE) {
    return [rsshubUrl(customBase, normalized)];
  }

  const candidates: string[] = [];

  // Собственный GitHub Pages-фид — первый приоритет
  const tgFeedBase = (process.env.TG_FEED_BASE ?? "").replace(/\/$/, "");
  if (tgFeedBase) {
    candidates.push(`${tgFeedBase}/${normalized}.xml`);
  }

  candidates.push(TG_RSS_TEMPLATE.replace("{channel}", normalized));
  for (const base of [DEFAULT_RSSHUB_BASE, ...RSSHUB_FALLBACKS]) {
    candidates.push(rsshubUrl(base, normalized));
  }
  return candidates;
};

export const fetchRss = async (url: string, limit = 8): Promise<RssItem[]> => {
  const feed = await parser.parseURL(url);
  return (feed.items ?? []).slice(0, limit).map(normalizeItem);
};

export const fetchTelegram = async (
  channel: string,
  rssUrlOverride?: string | null,
  limit = 8
): Promise<RssItem[]> => {
  if (rssUrlOverride) {
    return fetchRss(rssUrlOverride, limit);
  }

  const candidates = telegramCandidates(channel);
  let lastError: unknown = new Error("No Telegram RSS candidates");

  for (const url of candidates) {
    try {
      return await fetchRss(url, limit);
    } catch (error) {
      lastError = error;
    }
  }

  throw lastError;
};

export const fetchSourceNews = async (
  source: SourceInput,
  limit = 8
): Promise<RssItem[]> => {
  if (source.type === "rss") {
    if (!source.rssUrl) {
      throw new Error("RSS URL is required for rss sources");
    }
    return fetchRss(source.rssUrl, limit);
  }

  if (!source.channel && !source.rssUrl) {
    throw new Error("Telegram channel or RSS URL is required");
  }
  const channel = source.channel ?? "";
  return fetchTelegram(channel, source.rssUrl, limit);
};
