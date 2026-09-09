import { z } from 'zod';

export const PermissionSchema = z.object({
  id: z.number().int().positive(),
  name: z.string(),
  resource: z.string(),
  description: z.string().optional(),
  createdAt: z.string().optional(),
  updatedAt: z.string().optional(),
});
export type Permission = z.infer<typeof PermissionSchema>;

export const RouteSchema = z.object({
  id: z.number().int().positive(),
  path: z.string(),
  name: z.string(),
  createdAt: z.string().optional(),
});
export type Route = z.infer<typeof RouteSchema>;

export const MenuSchema = z.object({
  id: z.number().int().positive(),
  name: z.string(),
  path: z.string(),
  icon: z.string().optional(),
  parentId: z.number().nullable().optional(),
  createdAt: z.string().optional(),
});
export type Menu = z.infer<typeof MenuSchema>;

export const AssignRolesRequestSchema = z.object({
  roleIds: z.array(z.number().int().positive()),
});
export type AssignRolesRequest = z.infer<typeof AssignRolesRequestSchema>;

export const AssignPermissionsRequestSchema = z.object({
  permissionIds: z.array(z.number().int().positive()),
});
export type AssignPermissionsRequest = z.infer<typeof AssignPermissionsRequestSchema>;
