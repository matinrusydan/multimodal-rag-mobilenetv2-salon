import argon2 from 'argon2';
import { type UserRow, userRepository } from '../repositories/UserRepository';
import { HttpError } from '../utils/problemDetails';
import { permissionCache } from './PermissionCache';

export interface UserAdmin {
  id: number;
  name: string;
  username: string | null;
  email: string;
  type: number;
  status: string;
  validFrom: string | null;
  validTo: string | null;
  lastLoginAt: string | null;
  roleIds: number[];
  roles: string[];
  createdAt: string;
  updatedAt: string;
}

function map(row: UserRow, roles: string[], roleIds: number[]): UserAdmin {
  return {
    id: row.id,
    name: row.name,
    username: row.username,
    email: row.email,
    type: row.type,
    status: row.status,
    validFrom: row.valid_from ? String(row.valid_from).slice(0, 10) : null,
    validTo: row.valid_to ? String(row.valid_to).slice(0, 10) : null,
    lastLoginAt: row.last_login_at,
    roleIds,
    roles,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

export class UserService {
  async list(): Promise<UserAdmin[]> {
    const rows = await userRepository.list();
    const result: UserAdmin[] = [];
    for (const row of rows) {
      const [roles, roleIds] = await Promise.all([
        userRepository.findRoles(row.id),
        userRepository.findRoleIds(row.id),
      ]);
      result.push(
        map(
          row,
          roles.map((r) => r.code),
          roleIds,
        ),
      );
    }
    return result;
  }

  async get(id: number): Promise<UserAdmin> {
    const row = await userRepository.findById(id);
    if (!row) throw new HttpError(404, 'Pengguna tidak ditemukan');
    const [roles, roleIds] = await Promise.all([
      userRepository.findRoles(id),
      userRepository.findRoleIds(id),
    ]);
    return map(
      row,
      roles.map((r) => r.code),
      roleIds,
    );
  }

  async create(input: {
    name: string;
    username?: string | null;
    email: string;
    password: string;
    type?: number;
    status?: string;
    validFrom?: string | null;
    validTo?: string | null;
    roleIds?: number[];
  }): Promise<UserAdmin> {
    const existing = await userRepository.findByEmail(input.email);
    if (existing) throw new HttpError(409, 'Email sudah terdaftar');
    if (input.username) {
      const clash = await userRepository.findByUsername(input.username);
      if (clash) throw new HttpError(409, 'Username sudah dipakai');
    }
    const passwordHash = await argon2.hash(input.password, { type: argon2.argon2id });
    const user = await userRepository.create({
      name: input.name,
      username: input.username ?? null,
      email: input.email,
      password_hash: passwordHash,
      type: input.type ?? 1,
      status: input.status ?? 'active',
      valid_from: input.validFrom ?? null,
      valid_to: input.validTo ?? null,
    });
    if (input.roleIds?.length) {
      await userRepository.assignRoles(user.id, input.roleIds);
      permissionCache.invalidate(user.id);
    }
    return this.get(user.id);
  }

  async update(
    id: number,
    input: {
      name?: string;
      username?: string | null;
      email?: string;
      password?: string;
      type?: number;
      status?: string;
      validFrom?: string | null;
      validTo?: string | null;
      roleIds?: number[];
    },
  ): Promise<UserAdmin> {
    const current = await userRepository.findById(id);
    if (!current) throw new HttpError(404, 'Pengguna tidak ditemukan');
    if (input.email && input.email !== current.email) {
      const clash = await userRepository.findByEmail(input.email);
      if (clash) throw new HttpError(409, 'Email sudah terdaftar');
    }
    if (input.username && input.username !== current.username) {
      const clash = await userRepository.findByUsername(input.username);
      if (clash) throw new HttpError(409, 'Username sudah dipakai');
    }
    const password_hash = input.password
      ? await argon2.hash(input.password, { type: argon2.argon2id })
      : undefined;
    await userRepository.update(id, {
      name: input.name,
      username: input.username,
      email: input.email,
      type: input.type,
      status: input.status,
      valid_from: input.validFrom,
      valid_to: input.validTo,
      password_hash,
    });
    if (input.roleIds) {
      await userRepository.assignRoles(id, input.roleIds);
    }
    permissionCache.invalidate(id);
    return this.get(id);
  }

  async remove(id: number): Promise<void> {
    const current = await userRepository.findById(id);
    if (!current) throw new HttpError(404, 'Pengguna tidak ditemukan');
    if (current.type === 0) throw new HttpError(400, 'Superadmin tidak dapat dihapus');
    await userRepository.remove(id);
    permissionCache.invalidate(id);
  }

  async assignRoles(id: number, roleIds: number[]): Promise<UserAdmin> {
    const current = await userRepository.findById(id);
    if (!current) throw new HttpError(404, 'Pengguna tidak ditemukan');
    await userRepository.assignRoles(id, roleIds);
    permissionCache.invalidate(id);
    return this.get(id);
  }
}

export const userService = new UserService();
