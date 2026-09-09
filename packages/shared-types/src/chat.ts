import { z } from 'zod';
import { HairContextSchema } from './common';

export const ChatRequestSchema = z.object({
  message: z.string().trim().min(1, 'Pesan tidak boleh kosong').max(2000),
  hairContext: HairContextSchema.optional(),
  contextId: z.string().optional(),
});
export type ChatRequest = z.infer<typeof ChatRequestSchema>;

export const ChatSourceSchema = z.object({
  file: z.string(),
  snippet: z.string().optional(),
});
export type ChatSource = z.infer<typeof ChatSourceSchema>;

export const ChatResponseSchema = z.object({
  reply: z.string(),
  sources: z.array(ChatSourceSchema).default([]),
  contextId: z.string().optional(),
});
export type ChatResponse = z.infer<typeof ChatResponseSchema>;
