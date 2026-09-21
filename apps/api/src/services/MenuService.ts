import { type MenuRow, menuRepository } from '../repositories/MenuRepository';
import { HttpError } from '../utils/problemDetails';

export interface MenuAdmin {
  id: number;
  name: string;
  path: string;
  icon: string | null;
  parentId: number | null;
  sortOrder: number;
  status: string;
  roleIds: number[];
}

function map(row: MenuRow, roleIds: number[] = []): MenuAdmin {
  return {
    id: row.id,
    name: row.name,
    path: row.path,
    icon: row.icon,
    parentId: row.parent_id,
    sortOrder: row.sort_order,
    status: row.status,
    roleIds,
  };
}

export class MenuService {
  async list(): Promise<MenuAdmin[]> {
    const rows = await menuRepository.listWithRoles();
    return rows.map((r) => map(r, r.role_ids));
  }

  /** Menu untuk user yang sedang login (berdasarkan role). Super admin -> semua. */
  async listForRoles(roles: string[], isSuperAdmin: boolean): Promise<MenuAdmin[]> {
    const rows = isSuperAdmin
      ? await menuRepository.list()
      : await menuRepository.listByRoleCodes(roles);
    return rows.map((r) => map(r));
  }

  async get(id: number): Promise<MenuAdmin> {
    const row = await menuRepository.findById(id);
    if (!row) throw new HttpError(404, 'Menu tidak ditemukan');
    const roleIds = await menuRepository.findRoleIds(id);
    return map(row, roleIds);
  }

  async create(input: {
    name: string;
    path: string;
    icon?: string | null;
    parentId?: number | null;
    sortOrder?: number;
    status?: string;
    roleIds?: number[];
  }): Promise<MenuAdmin> {
    const row = await menuRepository.create({
      name: input.name,
      path: input.path,
      icon: input.icon ?? null,
      parent_id: input.parentId ?? null,
      sort_order: input.sortOrder ?? 0,
      status: input.status,
    });
    if (input.roleIds?.length) {
      await menuRepository.assignRoles(row.id, input.roleIds);
    }
    return this.get(row.id);
  }

  async update(
    id: number,
    input: {
      name?: string;
      path?: string;
      icon?: string | null;
      parentId?: number | null;
      sortOrder?: number;
      status?: string;
      roleIds?: number[];
    },
  ): Promise<MenuAdmin> {
    const current = await menuRepository.findById(id);
    if (!current) throw new HttpError(404, 'Menu tidak ditemukan');
    const row = await menuRepository.update(id, {
      name: input.name,
      path: input.path,
      icon: input.icon,
      parent_id: input.parentId,
      sort_order: input.sortOrder,
      status: input.status,
    });
    if (!row) throw new HttpError(404, 'Menu tidak ditemukan');
    if (input.roleIds) {
      await menuRepository.assignRoles(id, input.roleIds);
    }
    return this.get(id);
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
    return this.get(id);
  }
}

export const menuService = new MenuService();
