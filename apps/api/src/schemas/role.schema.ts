import { AssignPermissionsRequestSchema } from '@rag-salon/shared-types';
import { z } from 'zod';
import { idParamSchema } from './reservation.schema';

const createRoleBodySchema = z.object({
  name: z.string().trim().min(1, 'Nama role wajib diisi'),
  code: z
    .string()
    .trim()
    .min(1, 'Kode role wajib diisi')
    .regex(/^[A-Z0-9_]+$/, 'Kode role hanya huruf besar, angka, dan underscore'),
  parentId: z.coerce.number().int().positive().nullable().optional(),
  type: z.coerce.number().int().min(0).max(1).optional(),
  description: z.string().nullable().optional(),
});

const updateRoleBodySchema = createRoleBodySchema.partial();

export const createRoleSchema = { body: createRoleBodySchema };
export const updateRoleSchema = { body: updateRoleBodySchema };
export const roleParamsSchema = { params: idParamSchema };
export const assignRolePermissionsSchema = { body: AssignPermissionsRequestSchema };
