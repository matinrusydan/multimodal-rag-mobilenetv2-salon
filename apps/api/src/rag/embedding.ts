import OpenAI from 'openai';
import { env } from '../config/env';
import { logger } from '../config/logger';

let client: OpenAI | null = null;

export function getOpenAIClient(): OpenAI {
  if (!client) {
    if (!env.OPENAI_API_KEY || env.OPENAI_API_KEY.startsWith('sk-...')) {
      throw new Error('OPENAI_API_KEY belum diisi. Isi apps/api/.env lalu jalankan ulang proses.');
    }
    client = new OpenAI({ apiKey: env.OPENAI_API_KEY });
    logger.info({ embeddingModel: env.OPENAI_EMBEDDING_MODEL }, 'OpenAI client siap');
  }
  return client;
}

/**
 * Local embedding (offline, tanpa OpenAI). Feature-hashing sederhana:
 * huruf kecil + token kata + char-ngram -> FNV-1a -> slot vektor ber-tanda
 * -> normalisasi L2. Dim sama dengan text-embedding-3-small (1536) agar
 * collection ChromaDB tetap kompatibel. Digunakan saat
 * RAG_EMBEDDING_PROVIDER=local (smoke test / tanpa kredit OpenAI).
 */
const LOCAL_EMBEDDING_DIM = 1536;

function fnv1a(str: string): number {
  let h = 0x811c9dc5;
  for (let i = 0; i < str.length; i += 1) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h;
}

export function embedLocal(texts: string[]): number[][] {
  const vectors: number[][] = [];
  for (const text of texts) {
    const vec = new Array<number>(LOCAL_EMBEDDING_DIM).fill(0);
    const normalized = text.toLowerCase().replace(/\s+/g, ' ');
    const words = normalized.match(/[a-z0-9]{2,}/g) ?? [];
    const features = new Set<string>(words);
    for (const w of words) {
      features.add(`bi:${w.slice(0, 2)}`);
      features.add(`tri:${w.slice(0, 3)}`);
    }
    if (normalized.length > 4) {
      for (let i = 0; i + 3 <= normalized.length; i += 1) {
        features.add(`c3:${normalized.slice(i, i + 3)}`);
      }
    }
    for (const f of features) {
      const h = fnv1a(f);
      const idx = h % LOCAL_EMBEDDING_DIM;
      vec[idx] += h & 1 ? 1 : -1;
    }
    let norm = 0;
    for (const v of vec) norm += v * v;
    norm = Math.sqrt(norm) || 1;
    for (let i = 0; i < vec.length; i += 1) vec[i] /= norm;
    vectors.push(vec);
  }
  return vectors;
}

/**
 * Embed sekumpulan teks menjadi vektor.
 * - RAG_EMBEDDING_PROVIDER=local -> vektor 1536d lokal (offline).
 * - default (openai)               -> text-embedding-3-small 1536d.
 * Mendukung input string tunggal maupun array (diproses serempak).
 */
export async function embed(texts: string | string[]): Promise<number[][]> {
  const input = Array.isArray(texts) ? texts : [texts];
  if (env.RAG_EMBEDDING_PROVIDER === 'local') {
    logger.info({ provider: 'local', dim: LOCAL_EMBEDDING_DIM }, 'embedding lokal (offline)');
    return embedLocal(input);
  }
  const openai = getOpenAIClient();
  const res = await openai.embeddings.create({
    model: env.OPENAI_EMBEDDING_MODEL,
    input,
  });
  return res.data.map((d) => d.embedding);
}
