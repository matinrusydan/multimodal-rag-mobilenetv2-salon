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
}

export const serviceService = new ServiceService();
