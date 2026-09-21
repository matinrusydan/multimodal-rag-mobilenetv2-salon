import { type RoleRow, roleRepository } from '../repositories/RoleRepository';
import { HttpError } from '../utils/problemDetails';

export interface RoleAdmin {
  id: number;
  name: string;
  code: string;
  parentId: number | null;
  type: number;
  status: string;
  description: string | null;
  permissions: string[];
  createdAt: string;
  updatedAt: string;
}

export interface RoleAccess {
  roleId: number;
  routeIds: number[];
  permissionIds: number[];
  menuIds: number[];
}

function map(row: RoleRow, permissions: string[]): RoleAdmin {
  return {
    id: row.id,
    name: row.name,
    code: row.code,
    parentId: row.parent_id,
    type: row.type,
    status: row.status,
    description: row.description,
    permissions,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

export class RoleService {
  async list(): Promise<RoleAdmin[]> {
    const rows = await roleRepository.list();
    const result: RoleAdmin[] = [];
    for (const row of rows) {
      const permissionRows = await this.dbPermissions(row.id);
      result.push(map(row, permissionRows));
    }
    return result;
  }

  async get(id: number): Promise<RoleAdmin> {
    const row = await roleRepository.findById(id);
    if (!row) throw new HttpError(404, 'Role tidak ditemukan');
    return map(row, await this.dbPermissions(id));
  }

  /** Akses lengkap role: route (akses halaman), permission (render), menu. */
  async access(id: number): Promise<RoleAccess> {
    const row = await roleRepository.findById(id);
    if (!row) throw new HttpError(404, 'Role tidak ditemukan');
    const [routeIds, permissionIds, menuIds] = await Promise.all([
      roleRepository.findRouteIds(id),
      roleRepository.findPermissionIds(id),
      roleRepository.findMenuIds(id),
    ]);
    return { roleId: id, routeIds, permissionIds, menuIds };
  }

  async create(input: {
    name: string;
    code: string;
    parentId?: number | null;
    type?: number;
    status?: string;
    description?: string | null;
  }): Promise<RoleAdmin> {
    const existing = await roleRepository.findByCode(input.code);
    if (existing) throw new HttpError(409, 'Kode role sudah digunakan');
    const row = await roleRepository.create({
      name: input.name,
      code: input.code,
      parent_id: input.parentId ?? null,
      type: input.type,
      status: input.status,
      description: input.description,
    });
    return this.get(row.id);
  }

  async update(
    id: number,
    input: {
      name?: string;
      code?: string;
      parentId?: number | null;
      type?: number;
      status?: string;
      description?: string | null;
    },
  ): Promise<RoleAdmin> {
    const current = await roleRepository.findById(id);
    if (!current) throw new HttpError(404, 'Role tidak ditemukan');
    if (input.code && input.code !== current.code) {
      const clash = await roleRepository.findByCode(input.code);
      if (clash) throw new HttpError(409, 'Kode role sudah digunakan');
    }
    const row = await roleRepository.update(id, {
      name: input.name,
      code: input.code,
      parent_id: input.parentId,
      type: input.type,
      status: input.status,
      description: input.description,
    });
    if (!row) throw new HttpError(404, 'Role tidak ditemukan');
    return this.get(id);
  }

  async remove(id: number): Promise<void> {
    const current = await roleRepository.findById(id);
    if (!current) throw new HttpError(404, 'Role tidak ditemukan');
    if (current.type === 0) throw new HttpError(400, 'Role sistem tidak dapat dihapus');
    await roleRepository.remove(id);
  }

  async assignPermissions(id: number, permissionIds: number[]): Promise<RoleAdmin> {
    const current = await roleRepository.findById(id);
    if (!current) throw new HttpError(404, 'Role tidak ditemukan');
    await roleRepository.assignPermissions(id, permissionIds);
    return this.get(id);
  }

  async assignMenus(id: number, menuIds: number[]): Promise<RoleAccess> {
    const current = await roleRepository.findById(id);
    if (!current) throw new HttpError(404, 'Role tidak ditemukan');
    await roleRepository.assignMenus(id, menuIds);
    return this.access(id);
  }

  private async dbPermissions(roleId: number): Promise<string[]> {
    return roleRepository.findPermissionNames(roleId);
  }
}

export const roleService = new RoleService();
