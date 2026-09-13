import { ChromaClient, type Collection, IncludeEnum, type Metadata } from 'chromadb';
import { env } from '../config/env';
import { logger } from '../config/logger';

/** Topics / collections yang diinisialisasi saat startup. */
export const RAG_TOPICS = [
  'harga',
  'layanan',
  'gaya-rambut',
  'tips-perawatan',
  'booking-info',
] as const;

export type RagTopic = (typeof RAG_TOPICS)[number];

export interface VectorRecord {
  id: string;
  text: string;
  embedding: number[];
  metadata: Record<string, string | number>;
}

export interface VectorHit {
  id: string;
  text: string;
  distance: number;
  metadata: Record<string, string | number>;
}

/**
 * Wrapper persistent ChromaDB.
 * - Koneksi: HTTP ke server ChromaDB (CHROMA_URL). Persist dir server dikonfigurasi
 *   saat menjalankan server (mis. `chroma run --path ./chroma_db`).
 * - Collection satu per topic (harga, layanan, gaya-rambut, tips-perawatan, booking-info).
 */
export class VectorStore {
  private client: ChromaClient;
  private collections = new Map<RagTopic, Collection>();

  constructor(url: string = env.CHROMA_URL) {
    this.client = new ChromaClient({ path: url });
  }

  async init(): Promise<void> {
    for (const topic of RAG_TOPICS) {
      const col = await this.client.getOrCreateCollection({
        name: `rag-salon-${topic}`,
      });
      this.collections.set(topic, col);
    }
    logger.info({ topics: Array.from(this.collections.keys()) }, 'VectorStore: collection siap');
  }

  private async collection(topic: RagTopic): Promise<Collection> {
    let col = this.collections.get(topic);
    if (!col) {
      col = await this.client.getOrCreateCollection({ name: `rag-salon-${topic}` });
      this.collections.set(topic, col);
    }
    return col;
  }

  async upsert(topic: RagTopic, records: VectorRecord[]): Promise<void> {
    if (records.length === 0) return;
    const col = await this.collection(topic);
    await col.upsert({
      ids: records.map((r) => r.id),
      embeddings: records.map((r) => r.embedding),
      documents: records.map((r) => r.text),
      metadatas: records.map((r) => r.metadata as Metadata),
    });
    logger.debug({ topic, count: records.length }, 'VectorStore.upsert');
  }

  /** Query embedding terhadap satu topic. */
  async query(topic: RagTopic, embedding: number[], topK: number): Promise<VectorHit[]> {
    const col = await this.collection(topic);
    const res = await col.query({
      queryEmbeddings: embedding,
      nResults: topK,
      include: [IncludeEnum.Documents, IncludeEnum.Metadatas, IncludeEnum.Distances],
    });
    const docs = res.documents?.[0] ?? [];
    const dist = res.distances?.[0] ?? [];
    const metas = res.metadatas?.[0] ?? [];
    return docs.map((doc, i) => ({
      id: (res.ids?.[0]?.[i] as string) ?? String(i),
      text: doc ?? '',
      distance: dist[i] ?? 0,
      metadata: (metas[i] as Record<string, string | number> | null) ?? {},
    }));
  }

  /** Ambil seluruh id yang tersimpan (untuk diff idempotent). */
  async existingIds(topic: RagTopic): Promise<string[]> {
    const col = await this.collection(topic);
    const res = await col.get({ include: [] });
    return res.ids as string[];
  }

  /** Hapus record spesifik berdasarkan id. */
  async deleteByIds(topic: RagTopic, ids: string[]): Promise<void> {
    if (ids.length === 0) return;
    const col = await this.collection(topic);
    await col.delete({ ids });
  }

  /** Hapus seluruh records (utility, mis. re-ingest bersih). */
  async clear(topic: RagTopic): Promise<void> {
    const existing = await this.existingIds(topic);
    if (existing.length > 0) {
      const col = await this.collection(topic);
      await col.delete({ ids: existing });
    }
  }
}

export const vectorStore = new VectorStore();

/** Panggil saat bootstrap (app.ts) — koneksi & prep collection; gagal non-fatal. */
export function initVectorStore(): void {
  void vectorStore.init().catch((err) => {
    logger.warn(
      { err: (err as Error).message },
      'ChromaDB tidak tersedia; RAG menunggu ingest/manual init',
    );
  });
}
