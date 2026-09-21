import { type RouteRow, routeRepository } from '../repositories/RouteRepository';
import { HttpError } from '../utils/problemDetails';

export interface RouteAdmin {
  id: number;
  path: string;
  name: string;
  title: string | null;
  parentId: number | null;
  status: string;
  method: string | null;
  roleIds: number[];
}

function map(row: RouteRow, roleIds: number[] = []): RouteAdmin {
  return {
    id: row.id,
    path: row.path,
    name: row.name,
    title: row.title,
    parentId: row.parent_id,
    status: row.status,
    method: row.method,
    roleIds,
  };
}

export class RouteService {
  async list(): Promise<RouteAdmin[]> {
    const rows = await routeRepository.list();
    const result: RouteAdmin[] = [];
    for (const row of rows) {
      result.push(map(row, await routeRepository.findRoleIds(row.id)));
    }
    return result;
  }

  async get(id: number): Promise<RouteAdmin> {
    const row = await routeRepository.findById(id);
    if (!row) throw new HttpError(404, 'Route tidak ditemukan');
    return map(row, await routeRepository.findRoleIds(id));
  }

  async create(input: {
    path: string;
    name: string;
    title?: string | null;
    parentId?: number | null;
    status?: string;
    method?: string | null;
  }): Promise<RouteAdmin> {
    const row = await routeRepository.create({
      path: input.path,
      name: input.name,
      title: input.title ?? null,
      parent_id: input.parentId ?? null,
      status: input.status,
      method: input.method ?? null,
    });
    return this.get(row.id);
  }

  async update(
    id: number,
    input: {
      path?: string;
      name?: string;
      title?: string | null;
      parentId?: number | null;
      status?: string;
      method?: string | null;
    },
  ): Promise<RouteAdmin> {
    const current = await routeRepository.findById(id);
    if (!current) throw new HttpError(404, 'Route tidak ditemukan');
    const row = await routeRepository.update(id, {
      path: input.path,
      name: input.name,
      title: input.title,
      parent_id: input.parentId,
      status: input.status,
      method: input.method,
    });
    if (!row) throw new HttpError(404, 'Route tidak ditemukan');
    return this.get(id);
  }

  async remove(id: number): Promise<void> {
    const current = await routeRepository.findById(id);
    if (!current) throw new HttpError(404, 'Route tidak ditemukan');
    await routeRepository.remove(id);
  }

  async assignRoles(id: number, roleIds: number[]): Promise<RouteAdmin> {
    const current = await routeRepository.findById(id);
    if (!current) throw new HttpError(404, 'Route tidak ditemukan');
    await routeRepository.assignRoles(id, roleIds);
    return this.get(id);
  }
}

export const routeService = new RouteService();
