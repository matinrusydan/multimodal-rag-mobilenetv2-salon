import { BaseRepository } from './BaseRepository';

export interface RoleRow {
  id: number;
  name: string;
  code: string;
  parent_id: number | null;
  type: number;
  status: string;
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
    status?: string;
    description?: string | null;
  }): Promise<RoleRow> {
    const rows = await this.db<RoleRow>('roles').insert(input).returning('*');
    return rows[0];
  }

  async update(
    id: number,
    input: Partial<Pick<RoleRow, 'name' | 'code' | 'parent_id' | 'type' | 'status' | 'description'>>,
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

  async findRouteIds(roleId: number): Promise<number[]> {
    const rows = await this.db('role_routes').where({ role_id: roleId }).select('route_id');
    return rows.map((r) => r.route_id as number);
  }

  async findMenuIds(roleId: number): Promise<number[]> {
    const rows = await this.db('role_menus').where({ role_id: roleId }).select('menu_id');
    return rows.map((r) => r.menu_id as number);
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

  /** Assign akses MENU ke role (bukan permission). */
  async assignMenus(roleId: number, menuIds: number[]): Promise<void> {
    await this.db.transaction(async (trx) => {
      await trx('role_menus').where({ role_id: roleId }).del();
      if (menuIds.length > 0) {
        await trx('role_menus').insert(menuIds.map((menu_id) => ({ role_id: roleId, menu_id })));
      }
    });
  }

  /** Set akses MENU untuk SEMUA role (dipakai halaman matrix menu x role). */
  async setMenuRoles(menuId: number, roleIds: number[]): Promise<void> {
    await this.db.transaction(async (trx) => {
      await trx('role_menus').where({ menu_id: menuId }).del();
      if (roleIds.length > 0) {
        await trx('role_menus').insert(roleIds.map((role_id) => ({ role_id, menu_id: menuId })));
      }
    });
  }
}

export const roleRepository = new RoleRepository();
