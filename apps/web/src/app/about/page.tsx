import type { Metadata } from 'next';
import Image from 'next/image';

import { Section } from '@/components/ui/section';
import { StatCard } from '@/components/ui/stat-card';
import { salonInfo } from '@/data/salon-info';
import { Gem, HeartHandshake, Sparkles } from 'lucide-react';

export const metadata: Metadata = {
  title: 'Tentang',
  description: 'Cerita, visi, misi, keunggulan, dan statistik bisnis statis TIEN SALON.',
};

const values = [
  {
    title: 'Visi',
    description:
      'Menjadi salon rambut pilihan untuk pengalaman hair-care yang elegan, nyaman, dan mudah diakses.',
    icon: Sparkles,
  },
  {
    title: 'Misi',
    description:
      'Menghadirkan layanan rambut berkualitas melalui konsep reservasi digital yang modern.',
    icon: HeartHandshake,
  },
  {
    title: 'Keunggulan',
    description:
      'Menggabungkan ambience premium, layanan detail, dan pengalaman pelanggan yang rapi.',
    icon: Gem,
  },
];

export default function AboutPage() {
  return (
    <>
      <Section
        eyebrow="Tentang TIEN SALON"
        title="Salon rambut elegan untuk pengalaman hair-care yang terasa personal"
        description="Konten ini menggunakan mock copy sesuai kebutuhan static portfolio."
      >
        <div className="about-grid">
          <Image
            src="/images/hero/salon-hero.svg"
            alt="Visual salon TIEN SALON"
            width={1200}
            height={840}
          />
          <div className="about-copy">
            <p>
              TIEN SALON adalah konsep salon rambut modern yang mengutamakan kenyamanan, detail
              treatment rambut, dan pengalaman reservasi yang sederhana.
            </p>
            <p>
              Website portfolio ini memperlihatkan bagaimana calon pelanggan dapat mengenal layanan,
              memilih jadwal, dan mencoba alur reservasi tanpa backend.
            </p>
            <p>
              Setiap halaman disusun untuk menampilkan visual feminin, elegan, premium, dan clean.
            </p>
          </div>
        </div>
      </Section>
      <Section title="Visi, misi, dan keunggulan">
        <div className="benefit-grid">
          {values.map((item) => {
            const Icon = item.icon;
            return (
              <article key={item.title} className="benefit-card">
                <span>
                  <Icon size={24} />
                </span>
                <h3>{item.title}</h3>
                <p>{item.description}</p>
              </article>
            );
          })}
        </div>
      </Section>
      <Section title="Statistik bisnis statis">
        <div className="stats-grid">
          {salonInfo.stats.map((stat) => (
            <StatCard key={stat.label} value={stat.value} label={stat.label} />
          ))}
        </div>
      </Section>
    </>
  );
}
