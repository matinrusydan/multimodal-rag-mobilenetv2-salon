import { z } from 'zod';
import { ClassificationResultSchema, HairContextSchema } from './common';

export const AnalyzeResponseSchema = z.object({
  hairLength: ClassificationResultSchema,
  hairType: ClassificationResultSchema,
  analyzedAt: z.string(),
  status: z.enum(['ok', 'low_confidence']).default('ok'),
});
export type AnalyzeResponse = z.infer<typeof AnalyzeResponseSchema>;

/** Hasil CV yang dibekali ke konteks chat. */
export const CvContextSchema = HairContextSchema.extend({
  confidence: z.number().min(0).max(1).optional(),
});
export type CvContext = z.infer<typeof CvContextSchema>;
