import { BaseRepository } from './BaseRepository';

export interface RouteRow {
  id: number;
  path: string;
  name: string;
  method: string | null;
  created_at: string;
  updated_at: string;
}

export class RouteRepository extends BaseRepository {
  list(): Promise<RouteRow[]> {
    return this.db<RouteRow>('routes').orderBy('path');
  }

  findById(id: number): Promise<RouteRow | undefined> {
    return this.db<RouteRow>('routes').where({ id }).first();
  }

  async create(input: { path: string; name: string; method?: string | null }): Promise<RouteRow> {
    const rows = await this.db<RouteRow>('routes').insert(input).returning('*');
    return rows[0];
  }

  async update(
    id: number,
    input: Partial<Pick<RouteRow, 'path' | 'name' | 'method'>>,
  ): Promise<RouteRow | undefined> {
    await this.db<RouteRow>('routes')
      .where({ id })
      .update({ ...input, updated_at: this.db.fn.now() });
    return this.findById(id);
  }

  async remove(id: number): Promise<boolean> {
    await this.db('role_routes').where({ route_id: id }).del();
    return (await this.db('routes').where({ id }).del()) > 0;
  }
}

export const routeRepository = new RouteRepository();
