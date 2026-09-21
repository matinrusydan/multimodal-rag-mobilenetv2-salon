import type { Metadata } from 'next';

import { ResourceManager } from '@/components/admin/resource-manager';

export const metadata: Metadata = {
  title: 'Kelola Permissions',
};

export default function AdminPermissionsPage() {
  return <ResourceManager resource="permissions" />;
}
