import type { Metadata } from 'next';

import { CTABanner } from '@/components/sections/cta-banner';
import { FeaturedServices } from '@/components/sections/featured-services';
import { Hero } from '@/components/sections/hero';
import { Testimonials } from '@/components/sections/testimonials';
import { WhyChooseUs } from '@/components/sections/why-choose-us';

export const metadata: Metadata = {
  title: 'Beranda',
  description:
    'Landing page TIEN SALON dengan layanan unggulan, benefit salon, testimoni, dan CTA reservasi.',
  openGraph: {
    title: 'TIEN SALON — Reservasi Salon Modern',
    description:
      'Portfolio static website untuk katalog layanan dan simulasi reservasi TIEN SALON.',
    images: [
      {
        url: '/images/hero/salon-hero.svg',
        width: 1200,
        height: 630,
        alt: 'TIEN SALON',
      },
    ],
    url: '/home',
  },
};

export default function HomePage() {
  return (
    <>
      <Hero />
      <FeaturedServices />
      <WhyChooseUs />
      <Testimonials />
      <CTABanner />
    </>
  );
}
