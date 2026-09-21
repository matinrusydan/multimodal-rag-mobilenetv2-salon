import { BaseRepository } from './BaseRepository';

export interface MenuRow {
  id: number;
  name: string;
  path: string;
  icon: string | null;
  parent_id: number | null;
  sort_order: number;
  status: string;
  created_at: string;
  updated_at: string;
}

export class MenuRepository extends BaseRepository {
  list(): Promise<MenuRow[]> {
    return this.db<MenuRow>('menus').orderBy('sort_order');
  }

  /** Menu yang boleh diakses role tertentu (join role_menus). */
  listByRoleCodes(codes: string[]): Promise<MenuRow[]> {
    if (codes.length === 0) return Promise.resolve([]);
    return this.db<MenuRow>('menus')
      .distinct('menus.*')
      .join('role_menus', 'role_menus.menu_id', 'menus.id')
      .join('roles', 'roles.id', 'role_menus.role_id')
      .whereIn('roles.code', codes)
      .orderBy('menus.sort_order');
  }

  findById(id: number): Promise<MenuRow | undefined> {
    return this.db<MenuRow>('menus').where({ id }).first();
  }

  async create(input: {
    name: string;
    path: string;
    icon?: string | null;
    parent_id?: number | null;
    sort_order?: number;
    status?: string;
  }): Promise<MenuRow> {
    const rows = await this.db<MenuRow>('menus').insert(input).returning('*');
    return rows[0];
  }

  async update(
    id: number,
    input: Partial<Pick<MenuRow, 'name' | 'path' | 'icon' | 'parent_id' | 'sort_order' | 'status'>>,
  ): Promise<MenuRow | undefined> {
    await this.db<MenuRow>('menus')
      .where({ id })
      .update({ ...input, updated_at: this.db.fn.now() });
    return this.findById(id);
  }

  async remove(id: number): Promise<boolean> {
    await this.db('role_menus').where({ menu_id: id }).del();
    return (await this.db('menus').where({ id }).del()) > 0;
  }

  /** Semua menu + daftar role_ids yang punya akses (untuk matrix & list). */
  async listWithRoles(): Promise<Array<MenuRow & { role_ids: number[] }>> {
    const menus = await this.list();
    const links = await this.db('role_menus').select('menu_id', 'role_id');
    const byMenu = new Map<number, number[]>();
    for (const l of links) {
      const arr = byMenu.get(l.menu_id as number) ?? [];
      arr.push(l.role_id as number);
      byMenu.set(l.menu_id as number, arr);
    }
    return menus.map((m) => ({ ...m, role_ids: byMenu.get(m.id) ?? [] }));
  }

  async assignRoles(menuId: number, roleIds: number[]): Promise<void> {
    await this.db.transaction(async (trx) => {
      await trx('role_menus').where({ menu_id: menuId }).del();
      if (roleIds.length > 0) {
        await trx('role_menus').insert(roleIds.map((role_id) => ({ role_id, menu_id: menuId })));
      }
    });
  }

  async findRoleIds(menuId: number): Promise<number[]> {
    const rows = await this.db('role_menus').where({ menu_id: menuId }).select('role_id');
    return rows.map((r) => r.role_id as number);
  }
}

export const menuRepository = new MenuRepository();
