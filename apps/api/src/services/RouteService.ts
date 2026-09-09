import { type RouteRow, routeRepository } from '../repositories/RouteRepository';
import { HttpError } from '../utils/problemDetails';

export interface RouteAdmin {
  id: number;
  path: string;
  name: string;
  method: string | null;
}

function map(row: RouteRow): RouteAdmin {
  return {
    id: row.id,
    path: row.path,
    name: row.name,
    method: row.method,
  };
}

export class RouteService {
  async list(): Promise<RouteAdmin[]> {
    const rows = await routeRepository.list();
    return rows.map(map);
  }

  async get(id: number): Promise<RouteAdmin> {
    const row = await routeRepository.findById(id);
    if (!row) throw new HttpError(404, 'Route tidak ditemukan');
    return map(row);
  }

  async create(input: { path: string; name: string; method?: string | null }): Promise<RouteAdmin> {
    const row = await routeRepository.create(input);
    return map(row);
  }

  async update(
    id: number,
    input: { path?: string; name?: string; method?: string | null },
  ): Promise<RouteAdmin> {
    const current = await routeRepository.findById(id);
    if (!current) throw new HttpError(404, 'Route tidak ditemukan');
    const row = await routeRepository.update(id, input);
    if (!row) throw new HttpError(404, 'Route tidak ditemukan');
    return map(row);
  }

  async remove(id: number): Promise<void> {
    const current = await routeRepository.findById(id);
    if (!current) throw new HttpError(404, 'Route tidak ditemukan');
    await routeRepository.remove(id);
  }
}

export const routeService = new RouteService();
