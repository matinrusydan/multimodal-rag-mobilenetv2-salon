import type { ChatRequest, ChatResponse } from '@rag-salon/shared-types';
import { ragService } from './RagService';

export class ChatService {
  async chat(input: ChatRequest): Promise<ChatResponse> {
    const result = await ragService.answer(input.message, input.hairContext, input.hairFeatures);
    return {
      reply: result.reply,
      sources: result.sources,
      contextId: result.contextId,
    };
  }
}

export const chatService = new ChatService();
