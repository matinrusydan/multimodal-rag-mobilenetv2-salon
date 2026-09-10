import type { Metadata } from 'next';

import { ServiceGrid } from '@/components/services/service-grid';
import { Section } from '@/components/ui/section';
import { getServices } from '@/lib/catalog';

export const metadata: Metadata = {
  title: 'Layanan',
  description:
    'Katalog layanan TIEN SALON lengkap dengan harga, durasi, deskripsi, dan CTA reservasi.',
};

export const dynamic = 'force-dynamic';

export default async function ServicesPage() {
  const services = await getServices();
  return (
    <Section
      eyebrow="Katalog layanan"
      title="Pilih ritual rambut sesuai kebutuhanmu"
      description="Katalog layanan diambil dari API backend dan ditampilkan sebagai SSR content."
    >
      <ServiceGrid services={services} />
    </Section>
  );
}
