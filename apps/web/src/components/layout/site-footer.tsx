import { AtSign, MessageCircle, Music2 } from 'lucide-react';
import Link from 'next/link';

import { BrandLogo } from '@/components/brand/brand-logo';
import { Button } from '@/components/ui/button';
import { salonInfo } from '@/data/salon-info';
import { services } from '@/data/services';
import { cn } from '@/lib/utils';

type FooterLink = {
  label: string;
  href: string;
};

type FooterColumn = {
  title: string;
  links: FooterLink[];
};

type SiteFooterProps = {
  className?: string;
};

const socialIcons = {
  Instagram: AtSign,
  Facebook: AtSign,
  TikTok: Music2,
  WhatsApp: MessageCircle,
};

export function SiteFooter({ className }: SiteFooterProps) {
  const serviceLinks = services.slice(0, 4);

  return (
    <footer className={cn('site-footer', className)}>
      <div className="site-container site-footer__grid">
        <div className="site-footer__brand">
          <BrandLogo href="/home" />
          <p>{salonInfo.tagline}</p>
          <Button href="/reservation">Reservasi Sekarang</Button>
        </div>
        <div className="site-footer__column">
          <h3>Navigasi</h3>
          <Link href="/home">Beranda</Link>
          <Link href="/services">Layanan</Link>
          <Link href="/about">Tentang</Link>
          <Link href="/contact">Kontak</Link>
        </div>
        <div className="site-footer__column">
          <h3>Layanan</h3>
          {serviceLinks.map((service) => (
            <Link key={service.id} href={`/services/${service.slug}`}>
              {service.name}
            </Link>
          ))}
          <Link href="/services">Lihat Semua</Link>
        </div>
        <div className="site-footer__column">
          <h3>Informasi</h3>
          <Link href="/about">Tentang</Link>
          <Link href="/contact">Kontak</Link>
          <Link href="/login">Login</Link>
          <Link href="/register">Daftar</Link>
        </div>
      </div>
      <div className="site-container site-footer__bottom">
        <div>
          <h3>Jam Operasional</h3>
          {salonInfo.operatingHours.map((item) => (
            <p key={item.days}>
              {item.days}: {item.hours}
            </p>
          ))}
        </div>
        <div className="site-footer__socials">
          {salonInfo.socialLinks.map((social) => {
            const Icon = socialIcons[social.icon as keyof typeof socialIcons];

            return (
              <a key={social.platform} href={social.url} aria-label={social.platform}>
                {Icon ? <Icon size={18} /> : social.platform}
              </a>
            );
          })}
        </div>
        <p className="site-footer__copyright">© 2025 TIEN SALON. All rights reserved.</p>
      </div>
    </footer>
  );
}
