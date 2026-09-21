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
  title: z.string().optional(),
  parentId: z.number().nullable().optional(),
  status: z.string().optional(),
  method: z.string().nullable().optional(),
  createdAt: z.string().optional(),
});
export type Route = z.infer<typeof RouteSchema>;

export const MenuSchema = z.object({
  id: z.number().int().positive(),
  name: z.string(),
  path: z.string(),
  icon: z.string().nullable().optional(),
  parentId: z.number().nullable().optional(),
  sortOrder: z.number().optional(),
  status: z.string().optional(),
  createdAt: z.string().optional(),
});
export type Menu = z.infer<typeof MenuSchema>;

export const RbacRoleSchema = z.object({
  id: z.number().int().positive(),
  name: z.string(),
  code: z.string(),
  description: z.string().nullable().optional(),
  parentId: z.number().nullable().optional(),
  type: z.number().optional(),
  status: z.string().optional(),
});
export type RbacRole = z.infer<typeof RbacRoleSchema>;

export const RbacUserSchema = z.object({
  id: z.number().int().positive(),
  name: z.string(),
  username: z.string().nullable().optional(),
  email: z.string(),
  type: z.number().optional(),
  status: z.string().optional(),
  validFrom: z.string().nullable().optional(),
  validTo: z.string().nullable().optional(),
  roleIds: z.array(z.number()).optional(),
  roles: z.array(z.string()).optional(),
});
export type RbacUser = z.infer<typeof RbacUserSchema>;

export const AssignRolesRequestSchema = z.object({
  roleIds: z.array(z.number().int().positive()),
});
export type AssignRolesRequest = z.infer<typeof AssignRolesRequestSchema>;

export const AssignPermissionsRequestSchema = z.object({
  permissionIds: z.array(z.number().int().positive()),
});
export type AssignPermissionsRequest = z.infer<typeof AssignPermissionsRequestSchema>;
