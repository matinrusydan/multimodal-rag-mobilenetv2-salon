import { type MenuRow, menuRepository } from '../repositories/MenuRepository';
import { HttpError } from '../utils/problemDetails';

export interface MenuAdmin {
  id: number;
  name: string;
  path: string;
  icon: string | null;
  parentId: number | null;
  sortOrder: number;
}

function map(row: MenuRow): MenuAdmin {
  return {
    id: row.id,
    name: row.name,
    path: row.path,
    icon: row.icon,
    parentId: row.parent_id,
    sortOrder: row.sort_order,
  };
}

export class MenuService {
  async list(): Promise<MenuAdmin[]> {
    const rows = await menuRepository.list();
    return rows.map(map);
  }

  async get(id: number): Promise<MenuAdmin> {
    const row = await menuRepository.findById(id);
    if (!row) throw new HttpError(404, 'Menu tidak ditemukan');
    return map(row);
  }

  async create(input: {
    name: string;
    path: string;
    icon?: string | null;
    parentId?: number | null;
    sortOrder?: number;
  }): Promise<MenuAdmin> {
    const row = await menuRepository.create(input);
    return map(row);
  }

  async update(
    id: number,
    input: {
      name?: string;
      path?: string;
      icon?: string | null;
      parentId?: number | null;
      sortOrder?: number;
    },
  ): Promise<MenuAdmin> {
    const current = await menuRepository.findById(id);
    if (!current) throw new HttpError(404, 'Menu tidak ditemukan');
    const row = await menuRepository.update(id, input);
    if (!row) throw new HttpError(404, 'Menu tidak ditemukan');
    return map(row);
  }

  async remove(id: number): Promise<void> {
    const current = await menuRepository.findById(id);
    if (!current) throw new HttpError(404, 'Menu tidak ditemukan');
    await menuRepository.remove(id);
  }

  async assignRoles(id: number, roleIds: number[]): Promise<MenuAdmin> {
    const current = await menuRepository.findById(id);
    if (!current) throw new HttpError(404, 'Menu tidak ditemukan');
    await menuRepository.assignRoles(id, roleIds);
    return map(current);
  }
}

export const menuService = new MenuService();
