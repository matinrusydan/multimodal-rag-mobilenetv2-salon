import type { LoginRequest, RegisterRequest, User } from '@rag-salon/shared-types';
import argon2 from 'argon2';
import { signToken } from '../config/jwt';
import { roleRepository } from '../repositories/RoleRepository';
import { type UserRow, userRepository } from '../repositories/UserRepository';
import { HttpError } from '../utils/problemDetails';
import { permissionCache } from './PermissionCache';

export interface AuthResult {
  token: string;
  user: User;
}

export function toPublicUser(row: UserRow, roles: string[], permissions: string[]): User {
  return {
    id: row.id,
    name: row.name,
    email: row.email,
    type: row.type,
    roles: roles.map((code) => ({
      id: 0,
      name: code,
      code,
      parentId: null,
      type: 1,
      createdAt: '',
      updatedAt: '',
    })),
    permissions,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

export class AuthService {
  async register(input: RegisterRequest): Promise<AuthResult> {
    const existing = await userRepository.findByEmail(input.email);
    if (existing) {
      throw new HttpError(409, 'Email sudah terdaftar');
    }

    const passwordHash = await argon2.hash(input.password, { type: argon2.argon2id });
    const user = await userRepository.create({
      name: input.name,
      email: input.email,
      password_hash: passwordHash,
      type: 1,
    });

    const customerRole = await roleRepository.findByCode('CUSTOMER');
    if (customerRole) {
      await userRepository.assignRoles(user.id, [customerRole.id]);
    }

    const roles = await userRepository.findRoles(user.id);
    const permissions = await userRepository.findPermissions(user.id);
    permissionCache.set(user.id, permissions);

    return {
      token: signToken({ userId: user.id, name: user.name, email: user.email, type: user.type }),
      user: toPublicUser(
        user,
        roles.map((r) => r.code),
        permissions,
      ),
    };
  }

  async login(input: LoginRequest): Promise<AuthResult> {
    const user = await userRepository.findByEmail(input.email);
    if (!user || user.status !== 'active') {
      throw new HttpError(401, 'Email atau password salah');
    }

    const valid = await argon2.verify(user.password_hash, input.password);
    if (!valid) {
      throw new HttpError(401, 'Email atau password salah');
    }

    await userRepository.touchLastLogin(user.id);

    const roles = await userRepository.findRoles(user.id);
    let permissions = permissionCache.get(user.id);
    if (!permissions) {
      permissions = await userRepository.findPermissions(user.id);
      permissionCache.set(user.id, permissions);
    }

    return {
      token: signToken({ userId: user.id, name: user.name, email: user.email, type: user.type }),
      user: toPublicUser(
        user,
        roles.map((r) => r.code),
        permissions,
      ),
    };
  }

  async session(userId: number): Promise<User> {
    const user = await userRepository.findById(userId);
    if (!user) {
      throw new HttpError(401, 'Akun tidak ditemukan');
    }
    const roles = await userRepository.findRoles(userId);
    let permissions = permissionCache.get(userId);
    if (!permissions) {
      permissions = await userRepository.findPermissions(userId);
      permissionCache.set(userId, permissions);
    }
    return toPublicUser(
      user,
      roles.map((r) => r.code),
      permissions,
    );
  }

  logout(): { status: string } {
    return { status: 'logged_out' };
  }
}

export const authService = new AuthService();
