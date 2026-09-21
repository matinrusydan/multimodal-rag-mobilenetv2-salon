import type { Metadata } from 'next';

import { RolesManager } from '@/components/admin/roles-manager';

export const metadata: Metadata = {
  title: 'Kelola Roles',
};

export default function AdminRolesPage() {
  return <RolesManager />;
}
