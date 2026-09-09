import { Button } from '@/components/ui/button';

export function CTABanner() {
  return (
    <section className="site-section">
      <div className="site-container cta-banner">
        <div>
          <p className="section-heading__eyebrow">Siap reservasi?</p>
          <h2>Coba flow reservasi portfolio dari pilih layanan sampai payment sukses.</h2>
        </div>
        <Button href="/reservation" size="lg">
          Reservasi Sekarang
        </Button>
      </div>
    </section>
  );
}
