import { createHash } from 'node:crypto';
import type { HairContext } from '@rag-salon/shared-types';
import { env } from '../config/env';
import { logger } from '../config/logger';
import { embed, getOpenAIClient } from '../rag/embedding';
import { type HairFeatures, buildPrompt } from '../rag/promptBuilder';
import { type RetrievedDoc, retrieve } from '../rag/retriever';

export type { RetrievedDoc };

export interface RagResult {
  reply: string;
  sources: RetrievedDoc[];
  contextId: string;
}

function ctxHash(query: string, docIds: string[], hairContext?: HairContext): string {
  const raw = JSON.stringify({ query, hairContext, docIds });
  return `ctx-${createHash('sha256').update(raw).digest('hex').slice(0, 16)}`;
}

function fallbackReply(query: string, docs: RetrievedDoc[]): string {
  const lines = docs.slice(0, env.RAG_TOP_K).map((d, i) => {
    const source = d.file.replace(/\.md$/, '');
    const section = d.section ? ` — ${d.section}` : '';
    const snippet = (d.snippet ?? '').trim().replace(/\s+/g, ' ').slice(0, 240);
    return `${i + 1}. ${source}${section}\n   ${snippet}`;
  });
  return `(Mode offline — embed lokal, tanpa OpenAI.) Berdasarkan knowledge base untuk "${query}":\n\n${lines.join('\n')}`;
}

/**
 * RAG pipeline beneran: embed query -> retrieve top_k dari ChromaDB ->
 * prompt builder (system + docs + hair_context) -> GPT-4o-mini.
 * Saat RAG_EMBEDDING_PROVIDER=local, jawaban dibangun dari retrieved docs
 * (tanpa memanggil model — untuk testing/smoke tanpa kredit OpenAI).
 */
export class RagService {
  async answer(
    query: string,
    hairContext?: HairContext,
    hairFeatures?: HairFeatures,
  ): Promise<RagResult> {
    const isLocal = env.RAG_EMBEDDING_PROVIDER === 'local';

    const queryEmbeddings = await embed(query);
    const firstEmbedding = queryEmbeddings[0];
    if (!firstEmbedding) {
      throw new Error('Embedding query kosong');
    }
    const docs = await retrieve(firstEmbedding, {
      topK: env.RAG_TOP_K,
    });

    const contextId = ctxHash(
      query,
      docs.map((d) => `${d.file}#${d.section ?? ''}`),
      hairContext,
    );

    if (isLocal) {
      const reply = fallbackReply(query, docs);
      logger.info(
        { docs: docs.length, contextId, provider: 'local' },
        'RagService.answer (offline)',
      );
      return { reply, sources: docs.slice(0, env.RAG_TOP_K), contextId };
    }

    const messages = buildPrompt({ query, docs, hairContext, hairFeatures });
    const openai = getOpenAIClient();
    const completion = await openai.chat.completions.create({
      model: env.OPENAI_MODEL,
      messages,
      temperature: 0.7,
      max_tokens: 1000,
    });

    const reply = completion.choices[0]?.message.content?.trim() ?? '';
    logger.debug({ docs: docs.length, contextId }, 'RagService.answer selesai');
    return { reply, sources: docs.slice(0, env.RAG_TOP_K), contextId };
  }
}

export const ragService = new RagService();
