import { z } from 'zod';
import { idParamSchema } from './reservation.schema';

const createRouteBodySchema = z.object({
  path: z.string().trim().min(1, 'Path wajib diisi').startsWith('/', 'Path harus diawali /'),
  name: z.string().trim().min(1, 'Nama route wajib diisi'),
  title: z.string().trim().nullable().optional(),
  parentId: z.coerce.number().int().positive().nullable().optional(),
  status: z.enum(['active', 'inactive']).optional(),
  method: z.string().trim().max(10).nullable().optional(),
  roleIds: z.array(z.number().int().positive()).optional(),
});

const updateRouteBodySchema = createRouteBodySchema.partial();

export const createRouteSchema = { body: createRouteBodySchema };
export const updateRouteSchema = { body: updateRouteBodySchema };
export const routeParamsSchema = { params: idParamSchema };
export const assignRouteRolesSchema = {
  body: z.object({ roleIds: z.array(z.number().int().positive()) }),
};
