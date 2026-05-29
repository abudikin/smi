import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { fetchSourceNews } from "@/lib/rss";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const sourceId = searchParams.get("sourceId");
  const limit = Number(searchParams.get("limit") ?? "8");

  const limitValue = Number.isFinite(limit) && limit > 0 ? limit : 8;

  const sources = sourceId
    ? await prisma.source.findMany({ where: { id: sourceId } })
    : await prisma.source.findMany({ orderBy: { createdAt: "desc" } });

  const results = await Promise.all(
    sources.map(async (source) => {
      try {
        const items = await fetchSourceNews(
          {
            type: source.type,
            rssUrl: source.rssUrl,
            channel: source.channel,
          },
          limitValue
        );
        return { sourceId: source.id, label: source.label, items };
      } catch (error) {
        const message =
          error instanceof Error ? error.message : "Ошибка получения новостей";
        return { sourceId: source.id, label: source.label, error: message, items: [] };
      }
    })
  );

  return NextResponse.json({ results });
}
