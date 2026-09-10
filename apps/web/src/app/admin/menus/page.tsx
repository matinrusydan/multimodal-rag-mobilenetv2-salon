import type { Metadata } from 'next';

import { ResourceManager } from '@/components/admin/resource-manager';
import { menuResource } from '@/components/admin/specs';

export const metadata: Metadata = {
  title: 'Kelola Menus',
};

export default function AdminMenusPage() {
  return <ResourceManager spec={menuResource} />;
}
