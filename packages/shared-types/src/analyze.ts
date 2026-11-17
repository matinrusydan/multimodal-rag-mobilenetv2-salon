import { z } from 'zod';
import { ClassificationResultSchema, HairContextSchema, HairFeaturesSchema } from './common';

export const AnalyzeResponseSchema = z.object({
  hairLength: ClassificationResultSchema,
  hairType: ClassificationResultSchema,
  hairVolume: ClassificationResultSchema.nullable().optional(),
  tiedHair: z
    .object({
      tied: z.boolean().nullable(),
      style: z.string().nullable().optional(),
      confidence: z.number().min(0).max(1).nullable().optional(),
    })
    .optional(),
  hairFeatures: HairFeaturesSchema.optional(),
  geometry: z
    .object({
      head_units: z.number().nullable().optional(),
      relative_shoulder_ratio: z.number().nullable().optional(),
      method: z.string().nullable().optional(),
      hair_coverage: z.number().nullable().optional(),
      probabilities: z.record(z.number()).optional(),
    })
    .optional(),
  analyzedAt: z.string(),
  status: z.enum(['ok', 'low_confidence']).default('ok'),
});
export type AnalyzeResponse = z.infer<typeof AnalyzeResponseSchema>;

/** Hasil CV yang dibekali ke konteks chat. */
export const CvContextSchema = HairContextSchema.extend({
  confidence: z.number().min(0).max(1).optional(),
});
export type CvContext = z.infer<typeof CvContextSchema>;
