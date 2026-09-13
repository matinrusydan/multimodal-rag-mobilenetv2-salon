import { describe, expect, it } from 'vitest';
import { type StoreLike, retrieve } from '../../src/rag/retriever';
import { RAG_TOPICS, type RagTopic, type VectorHit } from '../../src/rag/vectorStore';

function hit(topic: string, distance: number, text?: string): VectorHit {
  return {
    id: `${topic}.md#abc#0`,
    text: text ?? `${topic} teks contoh`,
    distance,
    metadata: {
      file: `${topic}.md`,
      section: 'Bagian A',
      topic,
    },
  };
}

/** Fake store: distance deterministik per (topic, embedding[0]). */
class FakeStore implements StoreLike {
  async query(topic: RagTopic, embedding: number[], topK: number): Promise<VectorHit[]> {
    const dist = embedding[0] ?? 0;
    return Array.from({ length: topK }, (_, i) => hit(topic, dist + i * 0.1));
  }
}

describe('retriever', () => {
  it('menggabungkan hasil semua topic lalu mengambil top_k teratas', async () => {
    const store = new FakeStore();
    const results = await retrieve([0.5], { store, topics: RAG_TOPICS, topK: 5 });
    expect(results.length).toBeLessThanOrEqual(5);
    // topK=5, masih banyak hits dengan distance kecil -> diambil 5.
    expect(results).toHaveLength(5);
    // Terurut by distance naik.
    for (let i = 1; i < results.length; i++) {
      const prev = results[i - 1].distance;
      const cur = results[i].distance;
      expect(prev).toBeDefined();
      expect(cur).toBeDefined();
      expect(Number(cur) >= Number(prev)).toBe(true);
    }
  });

  it('memfilter hasil tanpa teks (distance tetap dipakai sebagai basis)', async () => {
    const store = new FakeStore();
    const results = await retrieve([1], { store, topics: ['harga', 'layanan'], topK: 3 });
    for (const r of results) {
      expect(r.snippet?.length).toBeGreaterThan(0);
      expect(r.file).toMatch(/\.md$/);
      expect(r.section).toBe('Bagian A');
    }
  });

  it('mengembalikan dokumen terimbang saat store satu topic error (di-skip)', async () => {
    const failing = {
      async query(topic: RagTopic, _embedding: number[], _topK: number) {
        if (topic === 'harga') throw new Error('boom');
        return [hit(topic, 0.2)];
      },
    } satisfies StoreLike;
    const results = await retrieve([0], { store: failing, topics: RAG_TOPICS, topK: 5 });
    expect(results.every((r) => r.file !== 'harga.md')).toBe(true);
    expect(results.length).toBeGreaterThan(0);
  });
});
