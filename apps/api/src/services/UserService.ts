import argon2 from 'argon2';
import { type UserRow, userRepository } from '../repositories/UserRepository';
import { HttpError } from '../utils/problemDetails';
import { permissionCache } from './PermissionCache';

export interface UserAdmin {
  id: number;
  name: string;
  email: string;
  type: number;
  status: string;
  lastLoginAt: string | null;
  roles: string[];
  createdAt: string;
  updatedAt: string;
}

function map(row: UserRow, roles: string[]): UserAdmin {
  return {
    id: row.id,
    name: row.name,
    email: row.email,
    type: row.type,
    status: row.status,
    lastLoginAt: row.last_login_at,
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
      const roles = await userRepository.findRoles(row.id);
      result.push(
        map(
          row,
          roles.map((r) => r.code),
        ),
      );
    }
    return result;
  }

  async get(id: number): Promise<UserAdmin> {
    const row = await userRepository.findById(id);
    if (!row) throw new HttpError(404, 'Pengguna tidak ditemukan');
    const roles = await userRepository.findRoles(id);
    return map(
      row,
      roles.map((r) => r.code),
    );
  }

  async create(input: {
    name: string;
    email: string;
    password: string;
    type?: number;
    roleIds?: number[];
  }): Promise<UserAdmin> {
    const existing = await userRepository.findByEmail(input.email);
    if (existing) throw new HttpError(409, 'Email sudah terdaftar');
    const passwordHash = await argon2.hash(input.password, { type: argon2.argon2id });
    const user = await userRepository.create({
      name: input.name,
      email: input.email,
      password_hash: passwordHash,
      type: input.type ?? 1,
    });
    if (input.roleIds?.length) {
      await userRepository.assignRoles(user.id, input.roleIds);
      permissionCache.invalidate(user.id);
    }
    return this.get(user.id);
  }

  async update(
    id: number,
    input: { name?: string; email?: string; password?: string; type?: number; status?: string },
  ): Promise<UserAdmin> {
    const current = await userRepository.findById(id);
    if (!current) throw new HttpError(404, 'Pengguna tidak ditemukan');
    if (input.email && input.email !== current.email) {
      const clash = await userRepository.findByEmail(input.email);
      if (clash) throw new HttpError(409, 'Email sudah terdaftar');
    }
    const password_hash = input.password
      ? await argon2.hash(input.password, { type: argon2.argon2id })
      : undefined;
    await userRepository.update(id, {
      name: input.name,
      email: input.email,
      type: input.type,
      status: input.status,
      password_hash,
    });
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
