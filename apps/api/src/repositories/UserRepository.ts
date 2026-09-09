import { BaseRepository } from './BaseRepository';

export interface UserRow {
  id: number;
  name: string;
  email: string;
  password_hash: string;
  type: number;
  status: string;
  last_login_at: string | null;
  created_at: string;
  updated_at: string;
}

interface RoleRow {
  id: number;
  code: string;
  name: string;
}

export class UserRepository extends BaseRepository {
  async findById(id: number): Promise<UserRow | undefined> {
    return this.db<UserRow>('users').where({ id }).first();
  }

  async findByEmail(email: string): Promise<UserRow | undefined> {
    return this.db<UserRow>('users').where({ email }).first();
  }

  list(): Promise<UserRow[]> {
    return this.db<UserRow>('users').orderBy('id');
  }

  async create(input: {
    name: string;
    email: string;
    password_hash: string;
    type?: number;
  }): Promise<UserRow> {
    const rows = await this.db<UserRow>('users').insert(input).returning('*');
    return rows[0];
  }

  async update(
    id: number,
    input: Partial<Pick<UserRow, 'name' | 'email' | 'type' | 'status' | 'password_hash'>>,
  ): Promise<UserRow | undefined> {
    await this.db<UserRow>('users')
      .where({ id })
      .update({ ...input, updated_at: this.db.fn.now() });
    return this.findById(id);
  }

  async remove(id: number): Promise<boolean> {
    const count = await this.db('user_roles').where({ user_id: id }).del();
    void count;
    return (await this.db('users').where({ id }).del()) > 0;
  }

  async findRoles(userId: number): Promise<RoleRow[]> {
    return this.db<RoleRow>('roles')
      .join('user_roles', 'roles.id', 'user_roles.role_id')
      .where('user_roles.user_id', userId)
      .select('roles.id', 'roles.code', 'roles.name');
  }

  async findPermissions(userId: number): Promise<string[]> {
    const rows = await this.db('permissions')
      .distinct('permissions.name')
      .join('role_permissions', 'permissions.id', 'role_permissions.permission_id')
      .join('user_roles', 'role_permissions.role_id', 'user_roles.role_id')
      .where('user_roles.user_id', userId);
    return rows.map((r) => r.name as string);
  }

  async assignRoles(userId: number, roleIds: number[]): Promise<void> {
    await this.db.transaction(async (trx) => {
      await trx('user_roles').where({ user_id: userId }).del();
      if (roleIds.length > 0) {
        await trx('user_roles').insert(roleIds.map((role_id) => ({ user_id: userId, role_id })));
      }
    });
  }

  async touchLastLogin(userId: number): Promise<void> {
    await this.db('users').where({ id: userId }).update({ last_login_at: this.db.fn.now() });
  }
}

export const userRepository = new UserRepository();
