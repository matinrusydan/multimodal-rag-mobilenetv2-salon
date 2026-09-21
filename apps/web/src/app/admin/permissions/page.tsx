import type { Metadata } from 'next';

import { PermissionsManager } from '@/components/admin/permissions-manager';

export const metadata: Metadata = {
  title: 'Kelola Permissions',
};

export default function AdminPermissionsPage() {
  return <PermissionsManager />;
}
