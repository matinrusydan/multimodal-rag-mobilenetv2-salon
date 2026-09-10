import type { Metadata } from 'next';

import { ConsultChat } from '@/components/consult/consult-chat';
import { Section } from '@/components/ui/section';

export const metadata: Metadata = {
  title: 'Konsultasi Rambut',
  description:
    'Chatbot konsultasi TIEN SALON berbasis RAG, dengan dukungan analisis foto rambut (CV).',
};

export default function ConsultPage() {
  return (
    <Section
      eyebrow="Konsultasi"
      title="Tanya tentang rambutmu"
      description="Chatbot berbasis RAG menjawab berdasarkan knowledge base salon. Unggah foto untuk analisis panjang & jenis rambut otomatis."
    >
      <ConsultChat />
    </Section>
  );
}
