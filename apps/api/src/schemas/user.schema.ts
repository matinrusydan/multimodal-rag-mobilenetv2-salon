import { AssignRolesRequestSchema } from '@rag-salon/shared-types';
import { z } from 'zod';
import { idParamSchema } from './reservation.schema';

const createUserBodySchema = z.object({
  name: z.string().trim().min(1, 'Nama wajib diisi'),
  email: z.string().trim().email('Email tidak valid'),
  password: z.string().min(8, 'Password minimal 8 karakter'),
  type: z.coerce.number().int().min(0).max(1).optional(),
  roleIds: z.array(z.number().int().positive()).optional(),
});

const updateUserBodySchema = z.object({
  name: z.string().trim().min(1).optional(),
  email: z.string().trim().email().optional(),
  password: z.string().min(8).optional(),
  type: z.coerce.number().int().min(0).max(1).optional(),
  status: z.enum(['active', 'inactive']).optional(),
});

export const createUserSchema = { body: createUserBodySchema };
export const updateUserSchema = { body: updateUserBodySchema };
export const userParamsSchema = { params: idParamSchema };
export const assignUserRolesSchema = { body: AssignRolesRequestSchema };
