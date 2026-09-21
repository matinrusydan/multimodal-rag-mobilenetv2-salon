import type { Metadata } from 'next';

import { MenusManager } from '@/components/admin/menus-manager';

export const metadata: Metadata = {
  title: 'Kelola Menus',
};

export default function AdminMenusPage() {
  return <MenusManager />;
}
