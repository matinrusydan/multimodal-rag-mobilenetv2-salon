import type { Metadata } from 'next';

import { ServiceDetail } from '@/components/services/service-detail';
import { services } from '@/data/services';
import { getServiceBySlug } from '@/lib/catalog';

type ServiceDetailPageProps = {
  params: Promise<{
    slug: string;
  }>;
};

export async function generateMetadata({ params }: ServiceDetailPageProps): Promise<Metadata> {
  const { slug } = await params;
  const service = await getServiceBySlug(slug);

  return {
    title: service ? service.name : 'Layanan Tidak Ditemukan',
    description:
      service?.shortDescription ?? 'Empty state layanan TIEN SALON untuk slug yang tidak valid.',
  };
}

export function generateStaticParams() {
  return services.map((service) => ({
    slug: service.slug,
  }));
}

export const dynamic = 'force-dynamic';

export default async function ServiceDetailPage({ params }: ServiceDetailPageProps) {
  const { slug } = await params;
  const service = await getServiceBySlug(slug);

  return (
    <main className="site-section">
      <ServiceDetail service={service} />
    </main>
  );
}
