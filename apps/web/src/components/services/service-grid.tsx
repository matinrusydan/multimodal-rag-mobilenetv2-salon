import { ServiceCard } from '@/components/services/service-card';
import type { Service } from '@/data/services';

type ServiceGridProps = {
  services: Service[];
};

export function ServiceGrid({ services }: ServiceGridProps) {
  return (
    <div className="service-grid service-grid--listing">
      {services.map((service) => (
        <ServiceCard key={service.id} service={service} />
      ))}
    </div>
  );
}
