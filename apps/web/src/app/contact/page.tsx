import { Mail, MapPin, Phone } from 'lucide-react';
import type { Metadata } from 'next';

import { Button } from '@/components/ui/button';
import { Section } from '@/components/ui/section';
import { salonInfo } from '@/data/salon-info';

export const metadata: Metadata = {
  title: 'Kontak',
  description: 'Informasi kontak, jam operasional, map preview, dan CTA reservasi TIEN SALON.',
};

export default function ContactPage() {
  return (
    <Section
      eyebrow="Kontak"
      title="Hubungi TIEN SALON"
      description="Informasi kontak dan lokasi statis untuk kebutuhan portfolio."
    >
      <div className="contact-grid">
        <div className="contact-card">
          <MapPin size={24} />
          <h2>Alamat</h2>
          <p>{salonInfo.address}</p>
        </div>
        <div className="contact-card">
          <Phone size={24} />
          <h2>Telepon</h2>
          <a href={`tel:${salonInfo.phone}`}>{salonInfo.phone}</a>
        </div>
        <div className="contact-card">
          <Mail size={24} />
          <h2>Email</h2>
          <a href={`mailto:${salonInfo.email}`}>{salonInfo.email}</a>
        </div>
      </div>
      <div className="contact-panel">
        <div>
          <h2>Jam Operasional</h2>
          {salonInfo.operatingHours.map((item) => (
            <p key={item.days}>
              <strong>{item.days}</strong>: {item.hours}
            </p>
          ))}
          <div className="contact-panel__socials">
            {salonInfo.socialLinks.map((social) => (
              <a key={social.platform} href={social.url}>
                {social.platform}
              </a>
            ))}
          </div>
          <Button href="/reservation">Reservasi Sekarang</Button>
        </div>
        <iframe
          title="Lokasi TIEN SALON"
          src={salonInfo.mapEmbedUrl}
          loading="lazy"
          referrerPolicy="no-referrer-when-downgrade"
        />
      </div>
    </Section>
  );
}
