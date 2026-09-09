import { ChevronRight, Sparkles } from 'lucide-react';
import Image from 'next/image';
import Link from 'next/link';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/ui/empty-state';
import { PriceDisplay } from '@/components/ui/price-display';
import type { Service } from '@/data/services';

type ServiceDetailProps = {
  service?: Service;
};

export function ServiceDetail({ service }: ServiceDetailProps) {
  if (!service) {
    return (
      <div className="site-container service-detail__empty">
        <EmptyState
          icon={<Sparkles size={26} />}
          title="Layanan ini tidak tersedia."
          description="Layanan yang kamu cari tidak ada di katalog mock data TIEN SALON."
          actionHref="/services"
          actionLabel="Kembali ke Katalog Layanan"
        />
      </div>
    );
  }

  return (
    <article className="site-container service-detail">
      <nav className="breadcrumb" aria-label="Breadcrumb">
        <Link href="/home">Home</Link>
        <ChevronRight size={16} />
        <Link href="/services">Layanan</Link>
        <ChevronRight size={16} />
        <span>{service.name}</span>
      </nav>
      <div className="service-detail__grid">
        <div className="service-detail__image">
          <Image
            src={service.image}
            alt={`Layanan ${service.name}`}
            width={720}
            height={520}
            priority
          />
        </div>
        <div className="service-detail__content">
          {service.isFeatured ? <Badge>Unggulan</Badge> : null}
          <h1>{service.name}</h1>
          <div className="service-detail__meta">
            <span>{service.category}</span>
            <span>{service.durationMinutes} menit</span>
          </div>
          <PriceDisplay price={service.price} discountPrice={service.discountPrice} />
          <p>{service.description}</p>
          <ul className="benefit-list">
            {service.benefits.map((benefit) => (
              <li key={benefit}>{benefit}</li>
            ))}
          </ul>
          <Button href="/reservation" size="lg">
            Reservasi Sekarang
          </Button>
        </div>
      </div>
    </article>
  );
}
