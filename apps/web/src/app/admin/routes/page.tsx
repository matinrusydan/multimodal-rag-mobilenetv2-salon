import type { Metadata } from 'next';

import { ResourceManager } from '@/components/admin/resource-manager';

export const metadata: Metadata = {
  title: 'Kelola Routes',
};

export default function AdminRoutesPage() {
  return <ResourceManager resource="routes" />;
}
