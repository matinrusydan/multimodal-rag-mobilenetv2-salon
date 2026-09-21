import type { Metadata } from 'next';

import { RoutesManager } from '@/components/admin/routes-manager';

export const metadata: Metadata = {
  title: 'Kelola Routes',
};

export default function AdminRoutesPage() {
  return <RoutesManager />;
}
