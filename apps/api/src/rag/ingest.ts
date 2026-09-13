/**
 * CLI ingestion knowledge base.
 * jalankan: pnpm rag:ingest  (dari apps/api)
 *
 * Membaca knowledge base (RAG_KNOWLEDGE_DIR, default ./rag/knowledge),
 * memecah per markdown -> chunk (500-1000 token, overlap 100) -> embed
 * (text-embedding-3-small) -> upsert ChromaDB per topic.
 *
 * Idempotent: id chunk = <file>#<hash-konten>#<index>. Chunk yang hash-nya
 * berubah akan di-upsert ulang; chunk yang tidak ada lagi dihapus.
 * --force menghapus seluruh collection topic dulu.
 */
import { createHash } from 'node:crypto';
import { readFile, readdir } from 'node:fs/promises';
import { join, resolve } from 'node:path';
import { z } from 'zod';
import { env } from '../config/env';
import { logger } from '../config/logger';
import { chunkMarkdown } from './chunker';
import { embed } from './embedding';
import { RAG_TOPICS, type RagTopic, vectorStore } from './vectorStore';

const args = z
  .object({ force: z.boolean().default(false) })
  .parse({ force: process.argv.includes('--force') });

const topicToFiles = new Map<RagTopic, string>([
  ['harga', 'harga.md'],
  ['layanan', 'layanan.md'],
  ['gaya-rambut', 'gaya-rambut.md'],
  ['tips-perawatan', 'tips-perawatan.md'],
  ['booking-info', 'booking-info.md'],
]);

function sha16(content: string): string {
  return createHash('sha256').update(content).digest('hex').slice(0, 16);
}

async function main(): Promise<void> {
  const dir = resolve(process.cwd(), env.RAG_KNOWLEDGE_DIR);
  const entries = await readdir(dir);
  const files = new Map(
    await Promise.all(
      entries
        .filter((e) => e.endsWith('.md'))
        .map(async (e) => [e, await readFile(join(dir, e), 'utf-8')] as const),
    ),
  );

  if (files.size === 0) {
    logger.warn({ dir }, 'Knowledge base kosong');
    return;
  }

  if (args.force) {
    for (const topic of RAG_TOPICS) {
      await vectorStore.clear(topic);
      logger.info({ topic }, 'collection di-clear (--force)');
    }
  }

  for (const [topic, filename] of topicToFiles) {
    const content = files.get(filename);
    if (!content) {
      logger.warn({ topic, filename }, 'file knowledge base tidak ditemukan, topic di-skip');
      continue;
    }

    const chunks = chunkMarkdown(content, {
      minTokens: env.RAG_MIN_CHUNK_TOKENS,
      maxTokens: env.RAG_MAX_CHUNK_TOKENS,
      overlapTokens: env.RAG_CHUNK_OVERLAP,
    });
    if (chunks.length === 0) {
      logger.warn({ topic }, 'tidak ada chunk, di-skip');
      continue;
    }

    const contentHash = sha16(content);
    const ids = chunks.map((_, i) => `${filename}#${contentHash}#${i}`);

    const existing = new Set(await vectorStore.existingIds(topic));
    const entries = chunks
      .map((chunk, i) => ({ chunk, id: ids[i] as string, index: i }))
      .filter((e) => !existing.has(e.id));
    const toDelete = [...existing].filter((id) => !ids.includes(id));

    if (entries.length > 0) {
      const texts = entries.map((e) => e.chunk.text);
      const embeddings = await embed(texts);
      await vectorStore.upsert(
        topic,
        entries.map((e, idx) => ({
          id: e.id,
          text: e.chunk.text,
          embedding: embeddings[idx] as number[],
          metadata: {
            file: filename,
            section: e.chunk.section,
            topic,
            hash: contentHash,
          },
        })),
      );
    }

    if (toDelete.length > 0) {
      await vectorStore.deleteByIds(topic, toDelete);
    }

    logger.info(
      { topic, chunks: chunks.length, upsert: entries.length, deleted: toDelete.length },
      'ingest selesai',
    );
  }
}

void main().catch((err) => {
  logger.error({ err }, 'ingest gagal');
  process.exitCode = 1;
});
