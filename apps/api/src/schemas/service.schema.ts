import { z } from 'zod';
import { idParamSchema } from './reservation.schema';

export const slugParamSchema = z.object({ slug: z.string().min(1) });

const createServiceBodySchema = z.object({
  name: z.string().trim().min(1, 'Nama layanan wajib diisi'),
  slug: z.string().trim().optional(),
  price: z.coerce.number().int().min(0, 'Harga tidak valid'),
  durationMin: z.coerce.number().int().min(1, 'Durasi minimal 1 menit'),
  description: z.string().nullable().optional(),
  category: z.string().nullable().optional(),
  image: z.string().nullable().optional(),
  isActive: z.boolean().optional(),
});

const updateServiceBodySchema = createServiceBodySchema.partial();

export const createServiceSchema = { body: createServiceBodySchema };
export const updateServiceSchema = { body: updateServiceBodySchema };
export const serviceIdParamSchema = { params: idParamSchema };
