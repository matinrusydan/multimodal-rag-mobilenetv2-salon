import { type PermissionRow, permissionRepository } from '../repositories/PermissionRepository';
import { HttpError } from '../utils/problemDetails';

export interface PermissionAdmin {
  id: number;
  name: string;
  resource: string;
  description: string | null;
}

function map(row: PermissionRow): PermissionAdmin {
  return {
    id: row.id,
    name: row.name,
    resource: row.resource,
    description: row.description,
  };
}

export class PermissionService {
  async list(): Promise<PermissionAdmin[]> {
    const rows = await permissionRepository.list();
    return rows.map(map);
  }

  async get(id: number): Promise<PermissionAdmin> {
    const row = await permissionRepository.findById(id);
    if (!row) throw new HttpError(404, 'Permission tidak ditemukan');
    return map(row);
  }

  async create(input: {
    name: string;
    resource: string;
    description?: string | null;
  }): Promise<PermissionAdmin> {
    const row = await permissionRepository.create(input);
    return map(row);
  }

  async update(
    id: number,
    input: { name?: string; resource?: string; description?: string | null },
  ): Promise<PermissionAdmin> {
    const current = await permissionRepository.findById(id);
    if (!current) throw new HttpError(404, 'Permission tidak ditemukan');
    const row = await permissionRepository.update(id, input);
    if (!row) throw new HttpError(404, 'Permission tidak ditemukan');
    return map(row);
  }

  async remove(id: number): Promise<void> {
    const current = await permissionRepository.findById(id);
    if (!current) throw new HttpError(404, 'Permission tidak ditemukan');
    await permissionRepository.remove(id);
  }
}

export const permissionService = new PermissionService();
