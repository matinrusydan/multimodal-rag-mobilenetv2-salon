import { Gem, HeartHandshake, Sparkles, WandSparkles } from 'lucide-react';

import { Section } from '@/components/ui/section';

const benefits = [
  {
    title: 'Terapis Profesional',
    description: 'Pengalaman perawatan dibuat nyaman dengan pendekatan yang detail dan ramah.',
    icon: HeartHandshake,
  },
  {
    title: 'Produk Berkualitas',
    description: 'Setiap treatment menonjolkan kualitas, kebersihan, dan rasa aman.',
    icon: Sparkles,
  },
  {
    title: 'Ambience Premium',
    description: 'Nuansa salon dirancang clean, feminin, dan menenangkan untuk perawatan rambut.',
    icon: Gem,
  },
  {
    title: 'Reservasi Mudah',
    description: 'Flow portfolio memperlihatkan proses reservasi sampai simulasi pembayaran.',
    icon: WandSparkles,
  },
];

export function WhyChooseUs() {
  return (
    <Section
      eyebrow="Mengapa TIEN SALON"
      title="Detail kecil yang membuat pengalaman terasa istimewa"
      description="Website ini menampilkan konsep layanan salon yang siap dikembangkan menjadi produk full-stack."
    >
      <div className="benefit-grid">
        {benefits.map((benefit) => {
          const Icon = benefit.icon;

          return (
            <article key={benefit.title} className="benefit-card">
              <span>
                <Icon size={24} />
              </span>
              <h3>{benefit.title}</h3>
              <p>{benefit.description}</p>
            </article>
          );
        })}
      </div>
    </Section>
  );
}
