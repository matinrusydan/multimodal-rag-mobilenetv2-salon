import { BaseRepository } from './BaseRepository';

export interface RouteRow {
  id: number;
  path: string;
  name: string;
  title: string | null;
  parent_id: number | null;
  status: string;
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

  async create(input: {
    path: string;
    name: string;
    title?: string | null;
    parent_id?: number | null;
    status?: string;
    method?: string | null;
  }): Promise<RouteRow> {
    const rows = await this.db<RouteRow>('routes').insert(input).returning('*');
    return rows[0];
  }

  async update(
    id: number,
    input: Partial<Pick<RouteRow, 'path' | 'name' | 'title' | 'parent_id' | 'status' | 'method'>>,
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

  async findRoleIds(routeId: number): Promise<number[]> {
    const rows = await this.db('role_routes').where({ route_id: routeId }).select('role_id');
    return rows.map((r) => r.role_id as number);
  }

  async assignRoles(routeId: number, roleIds: number[]): Promise<void> {
    await this.db.transaction(async (trx) => {
      await trx('role_routes').where({ route_id: routeId }).del();
      if (roleIds.length > 0) {
        await trx('role_routes').insert(roleIds.map((role_id) => ({ role_id, route_id: routeId })));
      }
    });
  }
}

export const routeRepository = new RouteRepository();
