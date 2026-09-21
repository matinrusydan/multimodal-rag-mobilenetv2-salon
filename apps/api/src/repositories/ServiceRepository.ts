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

  findById(id: number): Promise<ServiceRow | undefined> {
    return this.db<ServiceRow>('services').where({ id }).first();
  }

  async create(input: {
    name: string;
    slug: string;
    price: number;
    duration_min: number;
    description?: string | null;
    category?: string | null;
    image?: string | null;
    is_active?: boolean;
  }): Promise<ServiceRow> {
    const rows = await this.db<ServiceRow>('services').insert(input).returning('*');
    return rows[0];
  }

  async update(
    id: number,
    input: Partial<
      Pick<
        ServiceRow,
        'name' | 'slug' | 'price' | 'duration_min' | 'description' | 'category' | 'image' | 'is_active'
      >
    >,
  ): Promise<ServiceRow | undefined> {
    await this.db<ServiceRow>('services')
      .where({ id })
      .update({ ...input, updated_at: this.db.fn.now() });
    return this.findById(id);
  }

  async remove(id: number): Promise<boolean> {
    return (await this.db('services').where({ id }).del()) > 0;
  }

  /** Ringkasan per-kategori: jumlah, harga min/max, rata-rata durasi. */
  async categorySummary(): Promise<
    Array<{ category: string | null; count: number; min_price: number; max_price: number; avg_duration: number }>
  > {
    const rows = (await this.db('services')
      .where({ is_active: true })
      .groupBy('category')
      .select('category')
      .count({ count: '*' })
      .min({ min_price: 'price' })
      .max({ max_price: 'price' })
      .avg({ avg_duration: 'duration_min' })) as unknown as Array<{
      category: string | null;
      count: number | string;
      min_price: number | string | null;
      max_price: number | string | null;
      avg_duration: number | string | null;
    }>;
    return rows.map((r) => ({
      category: r.category ?? null,
      count: Number(r.count ?? 0),
      min_price: Number(r.min_price ?? 0),
      max_price: Number(r.max_price ?? 0),
      avg_duration: Number(r.avg_duration ?? 0),
    }));
  }

  /** Statistik publik: total layanan (aktif & nonaktif), harga min/max. */
  async publicStats(): Promise<{ total: number; active: number; min_price: number; max_price: number }> {
    const all = await this.db<ServiceRow>('services');
    const active = all.filter((s) => s.is_active);
    const prices = active.map((s) => s.price);
    return {
      total: all.length,
      active: active.length,
      min_price: prices.length ? Math.min(...prices) : 0,
      max_price: prices.length ? Math.max(...prices) : 0,
    };
  }
}

export const serviceRepository = new ServiceRepository();
