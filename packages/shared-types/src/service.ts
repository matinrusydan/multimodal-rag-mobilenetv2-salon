import { z } from 'zod';

export const ServiceSchema = z.object({
  id: z.number().int().positive(),
  name: z.string(),
  slug: z.string(),
  price: z.number().nonnegative(),
  durationMin: z.number().int().positive(),
  description: z.string(),
  category: z.string().optional(),
  image: z.string().optional(),
});
export type Service = z.infer<typeof ServiceSchema>;

export const ServiceListResponseSchema = z.array(ServiceSchema);
export type ServiceListResponse = z.infer<typeof ServiceListResponseSchema>;
