import { AssignRolesRequestSchema } from '@rag-salon/shared-types';
import { z } from 'zod';
import { idParamSchema } from './reservation.schema';

const createMenuBodySchema = z.object({
  name: z.string().trim().min(1, 'Nama menu wajib diisi'),
  path: z.string().trim().min(1, 'Path menu wajib diisi'),
  icon: z.string().trim().max(50).nullable().optional(),
  parentId: z.coerce.number().int().positive().nullable().optional(),
  sortOrder: z.coerce.number().int().min(0).optional(),
  status: z.enum(['active', 'inactive']).optional(),
  roleIds: z.array(z.number().int().positive()).optional(),
});

const updateMenuBodySchema = createMenuBodySchema.partial();

export const createMenuSchema = { body: createMenuBodySchema };
export const updateMenuSchema = { body: updateMenuBodySchema };
export const menuParamsSchema = { params: idParamSchema };
export const assignMenuRolesSchema = { body: AssignRolesRequestSchema };
