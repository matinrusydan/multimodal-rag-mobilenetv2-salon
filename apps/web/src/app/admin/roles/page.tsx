import type { Metadata } from 'next';

import { ResourceManager } from '@/components/admin/resource-manager';

export const metadata: Metadata = {
  title: 'Kelola Roles',
};

export default function AdminRolesPage() {
  return <ResourceManager resource="roles" />;
}
