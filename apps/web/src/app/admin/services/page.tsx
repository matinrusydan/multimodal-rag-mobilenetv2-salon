import type { Metadata } from 'next';

import { ServicesManager } from '@/components/admin/services-manager';

export const metadata: Metadata = {
  title: 'Kelola Layanan',
};

export default function AdminServicesPage() {
  return <ServicesManager />;
}
