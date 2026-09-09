import { BaseRepository } from './BaseRepository';

export interface ServiceRow {
  id: number;
  name: string;
  slug: string;
  price: number;
  duration_min: number;
  description: string | null;
  category: string | null;
  image: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export class ServiceRepository extends BaseRepository {
  listActive(): Promise<ServiceRow[]> {
    return this.db<ServiceRow>('services').where({ is_active: true }).orderBy('id');
  }

  all(): Promise<ServiceRow[]> {
    return this.db<ServiceRow>('services').orderBy('id');
  }

  findBySlug(slug: string): Promise<ServiceRow | undefined> {
    return this.db<ServiceRow>('services').where({ slug }).first();
  }

  findByIds(ids: number[]): Promise<ServiceRow[]> {
    return this.db<ServiceRow>('services').whereIn('id', ids).where({ is_active: true });
  }
}

export const serviceRepository = new ServiceRepository();
