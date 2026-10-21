import type { Metadata } from 'next';

import { ConsultChat } from '@/components/consult/consult-chat';
import { Section } from '@/components/ui/section';

export const metadata: Metadata = {
  title: 'Konsultasi Rambut',
  description:
    'Konsultasi teks TIEN SALON tentang perawatan rambut, layanan, dan harga berbasis RAG.',
};

export default function ConsultPage() {
  return (
    <Section
      eyebrow="Konsultasi"
      title="Tanya tentang rambutmu"
      description="Konsultasikan perawatan, layanan, dan harga melalui chatbot teks berbasis RAG. Analisis foto belum tersedia."
    >
      <ConsultChat />
    </Section>
  );
}
