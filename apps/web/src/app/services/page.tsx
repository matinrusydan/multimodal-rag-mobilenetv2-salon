import type { Metadata } from 'next';

import { ServiceGrid } from '@/components/services/service-grid';
import { Section } from '@/components/ui/section';
import { services } from '@/data/services';

export const metadata: Metadata = {
  title: 'Layanan',
  description:
    'Katalog layanan TIEN SALON lengkap dengan harga, durasi, deskripsi, dan CTA reservasi.',
};

export default function ServicesPage() {
  return (
    <Section
      eyebrow="Katalog layanan"
      title="Pilih ritual rambut sesuai kebutuhanmu"
      description="Semua layanan berasal dari mock data lokal dan ditampilkan sebagai static content."
    >
      <ServiceGrid services={services} />
    </Section>
  );
}
