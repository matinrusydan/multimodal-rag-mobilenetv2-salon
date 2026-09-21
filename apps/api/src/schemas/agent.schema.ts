import { z } from 'zod';

/**
 * Admin agent chat request.
 * Beda dari chat publik: mendukung riwayat percakapan multi-turn
 * agar agent bisa mengingat konteks dalam satu sesi widget.
 */
export const agentHistoryItemSchema = z.object({
  role: z.enum(['user', 'assistant']),
  content: z.string().min(1).max(4000),
});

export const agentChatSchema = {
  body: z.object({
    message: z.string().trim().min(1, 'Pesan tidak boleh kosong').max(2000),
    contextId: z.string().max(120).optional(),
    history: z.array(agentHistoryItemSchema).max(20).optional(),
  }),
};

export type AgentChatBody = z.infer<typeof agentChatSchema.body>;
