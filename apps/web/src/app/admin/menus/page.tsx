import type { Metadata } from 'next';

import { ResourceManager } from '@/components/admin/resource-manager';

export const metadata: Metadata = {
  title: 'Kelola Menus',
};

export default function AdminMenusPage() {
  return <ResourceManager resource="menus" />;
}
