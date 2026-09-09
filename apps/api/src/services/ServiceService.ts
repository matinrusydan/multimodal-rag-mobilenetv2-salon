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
}

export const serviceService = new ServiceService();
