import { BaseRepository } from './BaseRepository';

export interface PermissionRow {
  id: number;
  name: string;
  resource: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export class PermissionRepository extends BaseRepository {
  list(): Promise<PermissionRow[]> {
    return this.db<PermissionRow>('permissions').orderBy('resource', 'name');
  }

  findById(id: number): Promise<PermissionRow | undefined> {
    return this.db<PermissionRow>('permissions').where({ id }).first();
  }

  async create(input: {
    name: string;
    resource: string;
    description?: string | null;
  }): Promise<PermissionRow> {
    const rows = await this.db<PermissionRow>('permissions').insert(input).returning('*');
    return rows[0];
  }

  async update(
    id: number,
    input: Partial<Pick<PermissionRow, 'name' | 'resource' | 'description'>>,
  ): Promise<PermissionRow | undefined> {
    await this.db<PermissionRow>('permissions')
      .where({ id })
      .update({ ...input, updated_at: this.db.fn.now() });
    return this.findById(id);
  }

  async remove(id: number): Promise<boolean> {
    await this.db('role_permissions').where({ permission_id: id }).del();
    return (await this.db('permissions').where({ id }).del()) > 0;
  }
}

export const permissionRepository = new PermissionRepository();
