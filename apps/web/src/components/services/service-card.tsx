import Image from 'next/image';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { PriceDisplay } from '@/components/ui/price-display';
import type { Service } from '@/data/services';
import { cn } from '@/lib/utils';

type ServiceCardProps = {
  service: Service;
  className?: string;
};

export function ServiceCard({ service, className }: ServiceCardProps) {
  return (
    <article className={cn('service-card', className)}>
      <Image
        src={service.image}
        alt={`Layanan ${service.name}`}
        width={720}
        height={520}
        className="service-card__image"
      />
      {service.isFeatured ? <Badge className="service-card__badge">Unggulan</Badge> : null}
      <div className="service-card__body">
        <p className="service-card__duration">{service.durationMinutes} menit</p>
        <h3>{service.name}</h3>
        <p>{service.shortDescription}</p>
      </div>
      <div className="service-card__footer">
        <PriceDisplay price={service.price} discountPrice={service.discountPrice} />
        <Button href={`/services/${service.slug}`} variant="outline" size="sm">
          Detail
        </Button>
        <Button href="/reservation" size="sm">
          Reservasi
        </Button>
      </div>
    </article>
  );
}
