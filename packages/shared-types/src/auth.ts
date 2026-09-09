import { z } from 'zod';

export const RegisterRequestSchema = z.object({
  name: z.string().trim().min(1, 'Nama wajib diisi'),
  email: z.string().trim().email('Email tidak valid'),
  password: z.string().min(8, 'Password minimal 8 karakter'),
});
export type RegisterRequest = z.infer<typeof RegisterRequestSchema>;

export const LoginRequestSchema = z.object({
  email: z.string().trim().email('Email tidak valid'),
  password: z.string().min(1, 'Password wajib diisi'),
});
export type LoginRequest = z.infer<typeof LoginRequestSchema>;

export const RoleSchema = z.object({
  id: z.number().int().positive(),
  name: z.string(),
  code: z.string(),
  parentId: z.number().nullable(),
  type: z.number().default(1),
  createdAt: z.string().datetime(),
  updatedAt: z.string().datetime(),
});
export type Role = z.infer<typeof RoleSchema>;

export const UserSchema = z.object({
  id: z.number().int().positive(),
  name: z.string(),
  email: z.string().email(),
  type: z.number(),
  roles: z.array(RoleSchema).default([]),
  permissions: z.array(z.string()).default([]),
  createdAt: z.string().datetime(),
  updatedAt: z.string().datetime(),
});
export type User = z.infer<typeof UserSchema>;

export const LoginResponseSchema = z.object({
  token: z.string(),
  user: UserSchema,
});
export type LoginResponse = z.infer<typeof LoginResponseSchema>;

export const SessionResponseSchema = UserSchema;
export type SessionResponse = z.infer<typeof SessionResponseSchema>;
