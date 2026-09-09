import { BaseRepository } from './BaseRepository';

export interface MenuRow {
  id: number;
  name: string;
  path: string;
  icon: string | null;
  parent_id: number | null;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export class MenuRepository extends BaseRepository {
  list(): Promise<MenuRow[]> {
    return this.db<MenuRow>('menus').orderBy('sort_order');
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
  }): Promise<MenuRow> {
    const rows = await this.db<MenuRow>('menus').insert(input).returning('*');
    return rows[0];
  }

  async update(
    id: number,
    input: Partial<Pick<MenuRow, 'name' | 'path' | 'icon' | 'parent_id' | 'sort_order'>>,
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

  async assignRoles(menuId: number, roleIds: number[]): Promise<void> {
    await this.db.transaction(async (trx) => {
      await trx('role_menus').where({ menu_id: menuId }).del();
      if (roleIds.length > 0) {
        await trx('role_menus').insert(roleIds.map((role_id) => ({ role_id, menu_id: menuId })));
      }
    });
  }
}

export const menuRepository = new MenuRepository();
