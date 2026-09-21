import type { Service } from '@rag-salon/shared-types';
import { type ServiceRow, serviceRepository } from '../repositories/ServiceRepository';
import { HttpError } from '../utils/problemDetails';

function mapService(row: ServiceRow): Service {
  return {
    id: row.id,
    name: row.name,
    slug: row.slug,
    price: row.price,
    durationMin: row.duration_min,
    description: row.description ?? '',
    category: row.category ?? undefined,
    image: row.image ?? undefined,
  };
}

export interface ServiceAdmin extends Service {
  isActive: boolean;
}

function mapAdmin(row: ServiceRow): ServiceAdmin {
  return { ...mapService(row), isActive: row.is_active };
}

function slugify(text: string): string {
  return text
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

export class ServiceService {
  async list(): Promise<Service[]> {
    const rows = await serviceRepository.listActive();
    return rows.map(mapService);
  }

  async detail(slug: string): Promise<Service> {
    const row = await serviceRepository.findBySlug(slug);
    if (!row || !row.is_active) {
      throw new HttpError(404, 'Layanan tidak ditemukan');
    }
    return mapService(row);
  }

  /** Ringkasan untuk agent admin / dashboard. */
  async summary(): Promise<{
    stats: { total: number; active: number; minPrice: number; maxPrice: number };
    byCategory: Array<{
      category: string | null;
      count: number;
      minPrice: number;
      maxPrice: number;
      avgDurationMin: number;
    }>;
    services: Service[];
  }> {
    const [stats, byCategory, services] = await Promise.all([
      serviceRepository.publicStats(),
      serviceRepository.categorySummary(),
      this.list(),
    ]);
    return {
      stats: {
        total: stats.total,
        active: stats.active,
        minPrice: stats.min_price,
        maxPrice: stats.max_price,
      },
      byCategory: byCategory.map((c) => ({
        category: c.category,
        count: c.count,
        minPrice: c.min_price,
        maxPrice: c.max_price,
        avgDurationMin: Math.round(c.avg_duration),
      })),
      services,
    };
  }

  /** Daftar semua layanan (termasuk nonaktif) untuk admin. */
  async listAdmin(): Promise<ServiceAdmin[]> {
    const rows = await serviceRepository.all();
    return rows.map(mapAdmin);
  }

  async create(input: {
    name: string;
    slug?: string;
    price: number;
    durationMin: number;
    description?: string | null;
    category?: string | null;
    image?: string | null;
    isActive?: boolean;
  }): Promise<ServiceAdmin> {
    const slug = (input.slug || slugify(input.name)).trim();
    const existing = await serviceRepository.findBySlug(slug);
    if (existing) throw new HttpError(409, 'Slug layanan sudah dipakai');
    const row = await serviceRepository.create({
      name: input.name,
      slug,
      price: input.price,
      duration_min: input.durationMin,
      description: input.description ?? null,
      category: input.category ?? null,
      image: input.image ?? null,
      is_active: input.isActive ?? true,
    });
    return mapAdmin(row);
  }

  async update(
    id: number,
    input: {
      name?: string;
      slug?: string;
      price?: number;
      durationMin?: number;
      description?: string | null;
      category?: string | null;
      image?: string | null;
      isActive?: boolean;
    },
  ): Promise<ServiceAdmin> {
    const current = await serviceRepository.findById(id);
    if (!current) throw new HttpError(404, 'Layanan tidak ditemukan');
    if (input.slug && input.slug !== current.slug) {
      const clash = await serviceRepository.findBySlug(input.slug);
      if (clash) throw new HttpError(409, 'Slug layanan sudah dipakai');
    }
    const row = await serviceRepository.update(id, {
      name: input.name,
      slug: input.slug,
      price: input.price,
      duration_min: input.durationMin,
      description: input.description,
      category: input.category,
      image: input.image,
      is_active: input.isActive,
    });
    if (!row) throw new HttpError(404, 'Layanan tidak ditemukan');
    return mapAdmin(row);
  }

  async remove(id: number): Promise<void> {
    const current = await serviceRepository.findById(id);
    if (!current) throw new HttpError(404, 'Layanan tidak ditemukan');
    try {
      await serviceRepository.remove(id);
    } catch {
      throw new HttpError(409, 'Layanan tidak dapat dihapus karena dipakai reservasi');
    }
  }
}

export const serviceService = new ServiceService();
