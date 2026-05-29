import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { SourceType } from "@prisma/client";

const normalizePayload = (payload: Record<string, unknown>) => {
  const label = String(payload.label ?? "").trim();
  const type = String(payload.type ?? "").toLowerCase();
  const rssUrl = String(payload.rssUrl ?? "").trim();
  const channel = String(payload.channel ?? "").trim().replace(/^@/, "");

  return {
    label,
    type,
    rssUrl: rssUrl || null,
    channel: channel || null,
  };
};

const validatePayload = (payload: ReturnType<typeof normalizePayload>) => {
  if (!payload.label) {
    return "Поле label обязательно.";
  }
  if (payload.type !== "rss" && payload.type !== "telegram") {
    return "Поле type должно быть rss или telegram.";
  }
  if (payload.type === "rss" && !payload.rssUrl) {
    return "Для типа rss обязателен rssUrl.";
  }
  if (payload.type === "telegram" && !payload.channel && !payload.rssUrl) {
    return "Для типа telegram укажите channel или rssUrl.";
  }
  return null;
};

export const dynamic = "force-dynamic";

export async function GET() {
  const sources = await prisma.source.findMany({
    orderBy: { createdAt: "desc" },
  });
  return NextResponse.json({ sources });
}

export async function POST(request: Request) {
  const body = (await request.json()) as Record<string, unknown>;
  const normalized = normalizePayload(body);
  const error = validatePayload(normalized);

  if (error) {
    return NextResponse.json({ error }, { status: 400 });
  }

  const created = await prisma.source.create({
    data: {
      label: normalized.label,
      type: normalized.type as SourceType,
      rssUrl: normalized.rssUrl,
      channel: normalized.channel,
    },
  });

  return NextResponse.json({ source: created });
}
