import type { RagTopic, VectorHit } from './vectorStore';
import { RAG_TOPICS, vectorStore } from './vectorStore';

/** Dokumen yang diambil sebagai konteks jawaban. */
export interface RetrievedDoc {
  file: string;
  section?: string;
  snippet?: string;
  distance?: number;
}

export interface StoreLike {
  query(topic: RagTopic, embedding: number[], topK: number): Promise<VectorHit[]>;
}

export interface RetrieverOptions {
  store?: StoreLike;
  topics?: readonly RagTopic[];
  topK?: number;
}

/**
 * Retrieval cosine-similarity dari seluruh collection topic,
 * digabung lalu diambil top_k teratas berdasarkan distance (kecil = mirip).
 */
export async function retrieve(
  embedding: number[],
  options: RetrieverOptions = {},
): Promise<RetrievedDoc[]> {
  const store = options.store ?? vectorStore;
  const topics = options.topics ?? RAG_TOPICS;
  const topK = options.topK ?? 0; // caller pas; default kosong bila 0

  const perTopic = Math.max(1, Math.ceil(topK / topics.length));

  const results = await Promise.all(
    topics.map(async (topic) => {
      try {
        return await store.query(topic, embedding, perTopic);
      } catch {
        return [] as VectorHit[];
      }
    }),
  );

  const merged = flatMap(results)
    .filter((h) => h.text.length > 0)
    .sort((a, b) => a.distance - b.distance);

  const taken = topK > 0 ? merged.slice(0, topK) : merged;

  return taken.map((h) => ({
    file:
      (typeof h.metadata.file === 'string' && h.metadata.file) ||
      String(h.id.split('#')[0] ?? 'rag'),
    section: typeof h.metadata.section === 'string' ? h.metadata.section : undefined,
    snippet: h.text,
    distance: h.distance,
  }));
}

function flatMap(hits: VectorHit[][]): VectorHit[] {
  return hits.reduce((acc, h) => acc.concat(h), [] as VectorHit[]);
}

export { RAG_TOPICS };
export type { RagTopic, VectorHit };
