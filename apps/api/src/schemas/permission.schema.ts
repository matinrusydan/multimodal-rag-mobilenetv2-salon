import { z } from 'zod';
import { idParamSchema } from './reservation.schema';

const createPermissionBodySchema = z.object({
  name: z
    .string()
    .trim()
    .min(1, 'Nama permission wajib diisi')
    .regex(/^[a-z]+\.[a-zA-Z.*]+$/, 'Format permission harus resource.action'),
  resource: z.string().trim().min(1, 'Resource wajib diisi'),
  description: z.string().nullable().optional(),
});

const updatePermissionBodySchema = createPermissionBodySchema.partial();

export const createPermissionSchema = { body: createPermissionBodySchema };
export const updatePermissionSchema = { body: updatePermissionBodySchema };
export const permissionParamsSchema = { params: idParamSchema };
