/**
 * STUB — implementasi penuh (ChromaDB + OpenAI text-embedding-3-small + GPT-4o-mini) di Phase 07.
 */
export interface RetrievedDoc {
  file: string;
  snippet?: string;
}

export interface RagResult {
  reply: string;
  sources: RetrievedDoc[];
  contextId: string;
}

export class RagService {
  async retrieve(_query: string): Promise<RetrievedDoc[]> {
    return [{ file: 'gaya-rambut.md' }];
  }

  async answer(
    query: string,
    hairContext: { hairLength: string; hairType: string } | undefined,
  ): Promise<RagResult> {
    const contextLabel = hairContext
      ? `${hairContext.hairLength} ${hairContext.hairType}`
      : 'rambut Anda';
    return {
      reply: `Untuk ${contextLabel}, rekomendasi dari TIEN SALON: gunakan perawatan yang menyesuaikan tekstur rambut. ${query}`,
      sources: await this.retrieve(query),
      contextId: `ctx-${Date.now()}`,
    };
  }
}

export const ragService = new RagService();
