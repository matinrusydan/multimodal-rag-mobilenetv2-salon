import type { Service as ApiService } from '@rag-salon/shared-types';

import {
  type Service,
  getServiceBySlug as getLocalServiceBySlug,
  services as localServices,
} from '@/data/services';
import { backendRequest } from '@/lib/backend';

const PALETTE = ['#B3A8C9', '#A3B899', '#C9B3A8', '#B5838D', '#A2B9BC', '#E8B4B8'];

const localBySlug = new Map(localServices.map((service) => [service.slug, service]));

function toLocalService(api: ApiService, index: number): Service {
  const local = localBySlug.get(api.slug);
  return {
    id: String(api.id),
    slug: api.slug,
    name: api.name,
    shortDescription: local?.shortDescription ?? api.description ?? api.name,
    description: api.description ?? local?.description ?? '',
    image: api.image ?? local?.image ?? '/images/services/creambath.png',
    price: api.price,
    discountPrice:
      local?.discountPrice !== undefined && local.discountPrice < api.price
        ? local.discountPrice
        : undefined,
    durationMinutes: api.durationMin ?? local?.durationMinutes ?? 60,
    isFeatured: local?.isFeatured ?? false,
    benefits: local?.benefits ?? [],
    category: api.category ?? local?.category ?? 'Layanan',
    color: local?.color ?? PALETTE[index % PALETTE.length],
  };
}

export async function getServices(): Promise<Service[]> {
  try {
    const list = await backendRequest<ApiService[]>('/services');
    if (!Array.isArray(list) || list.length === 0) {
      return localServices;
    }
    return list.map(toLocalService);
  } catch {
    return localServices;
  }
}

export async function getServiceBySlug(slug: string): Promise<Service | undefined> {
  const list = await getServices();
  return list.find((service) => service.slug === slug) ?? getLocalServiceBySlug(slug);
}
