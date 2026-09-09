import { BaseRepository } from './BaseRepository';

export interface RoleRow {
  id: number;
  name: string;
  code: string;
  parent_id: number | null;
  type: number;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export class RoleRepository extends BaseRepository {
  list(): Promise<RoleRow[]> {
    return this.db<RoleRow>('roles').orderBy('id');
  }

  findById(id: number): Promise<RoleRow | undefined> {
    return this.db<RoleRow>('roles').where({ id }).first();
  }

  findByCode(code: string): Promise<RoleRow | undefined> {
    return this.db<RoleRow>('roles').where({ code }).first();
  }

  async create(input: {
    name: string;
    code: string;
    parent_id?: number | null;
    type?: number;
    description?: string | null;
  }): Promise<RoleRow> {
    const rows = await this.db<RoleRow>('roles').insert(input).returning('*');
    return rows[0];
  }

  async update(
    id: number,
    input: Partial<Pick<RoleRow, 'name' | 'code' | 'parent_id' | 'type' | 'description'>>,
  ): Promise<RoleRow | undefined> {
    await this.db<RoleRow>('roles')
      .where({ id })
      .update({ ...input, updated_at: this.db.fn.now() });
    return this.findById(id);
  }

  async remove(id: number): Promise<boolean> {
    await this.db.transaction(async (trx) => {
      await trx('role_permissions').where({ role_id: id }).del();
      await trx('role_routes').where({ role_id: id }).del();
      await trx('role_menus').where({ role_id: id }).del();
      await trx('user_roles').where({ role_id: id }).del();
      await trx('roles').where({ id }).del();
    });
    return true;
  }

  async findPermissionIds(roleId: number): Promise<number[]> {
    const rows = await this.db('role_permissions')
      .where({ role_id: roleId })
      .select('permission_id');
    return rows.map((r) => r.permission_id as number);
  }

  async findPermissionNames(roleId: number): Promise<string[]> {
    const rows = await this.db('permissions')
      .join('role_permissions', 'permissions.id', 'role_permissions.permission_id')
      .where('role_permissions.role_id', roleId)
      .orderBy('permissions.resource', 'permissions.name')
      .select('permissions.name');
    return rows.map((r) => r.name as string);
  }

  async assignPermissions(roleId: number, permissionIds: number[]): Promise<void> {
    await this.db.transaction(async (trx) => {
      await trx('role_permissions').where({ role_id: roleId }).del();
      if (permissionIds.length > 0) {
        await trx('role_permissions').insert(
          permissionIds.map((permission_id) => ({ role_id: roleId, permission_id })),
        );
      }
    });
  }
}

export const roleRepository = new RoleRepository();
