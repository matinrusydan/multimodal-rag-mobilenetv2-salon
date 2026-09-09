import { z } from 'zod';

/** Label klasifikasi tetap — JANGAN diubah (lihat PRD). */
export const HAIR_LENGTH_LABELS = ['pendek', 'pendek-menengah', 'menengah', 'panjang'] as const;

export const HAIR_TYPE_LABELS = ['lurus', 'bergelombang', 'keriting', 'sangat-keriting'] as const;

export const HairLengthLabelSchema = z.enum(HAIR_LENGTH_LABELS);
export type HairLengthLabel = z.infer<typeof HairLengthLabelSchema>;

export const HairTypeLabelSchema = z.enum(HAIR_TYPE_LABELS);
export type HairTypeLabel = z.infer<typeof HairTypeLabelSchema>;

export const HairContextSchema = z.object({
  hairLength: HairLengthLabelSchema,
  hairType: HairTypeLabelSchema,
});
export type HairContext = z.infer<typeof HairContextSchema>;

export const ClassificationResultSchema = z.object({
  label: z.string(),
  confidence: z.number().min(0).max(1),
});
export type ClassificationResult = z.infer<typeof ClassificationResultSchema>;

/** Format respons sukses standar: { ok: true, data } */
export const ApiSuccessSchema = <T extends z.ZodType>(data: T) =>
  z.object({ ok: z.literal(true), data });
