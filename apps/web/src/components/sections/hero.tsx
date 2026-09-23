import { HairScissorsHeroVisual } from '@/components/sections/hair-scissors-hero-visual';
import { Button } from '@/components/ui/button';
import { salonInfo as fallback } from '@/data/salon-info';

export function Hero({ tagline }: { tagline?: string }) {
  const text = tagline || fallback.tagline;
  return (
    <section className="hero-section">
      <div className="site-container hero-section__grid">
        <div className="section-heading">
          <p className="section-heading__eyebrow">Reservasi salon modern</p>
          <h1>
            Tampil cantik dan percaya diri bersama <span>TIEN SALON</span>
          </h1>
          <p>
            {text} Jelajahi layanan, pilih jadwal, dan coba alur reservasi portfolio secara
            statis.
          </p>
          <div className="hero-section__actions">
            <Button href="/reservation" size="lg">
              Reservasi Sekarang
            </Button>
            <Button href="/services" variant="secondary" size="lg">
              Lihat Layanan
            </Button>
          </div>
        </div>
        <div className="hero-section__visual">
          <HairScissorsHeroVisual />
        </div>
      </div>
    </section>
  );
}
