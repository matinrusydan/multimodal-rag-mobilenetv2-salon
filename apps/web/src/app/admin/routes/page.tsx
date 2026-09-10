import type { Metadata } from 'next';

import { ResourceManager } from '@/components/admin/resource-manager';
import { routeResource } from '@/components/admin/specs';

export const metadata: Metadata = {
  title: 'Kelola Routes',
};

export default function AdminRoutesPage() {
  return <ResourceManager spec={routeResource} />;
}
