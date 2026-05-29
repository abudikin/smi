-- CreateEnum
CREATE TYPE "SourceType" AS ENUM ('rss', 'telegram');

-- CreateTable
CREATE TABLE "Source" (
    "id" TEXT NOT NULL,
    "label" TEXT NOT NULL,
    "type" "SourceType" NOT NULL,
    "rssUrl" TEXT,
    "channel" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "Source_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "Source_type_idx" ON "Source"("type");
