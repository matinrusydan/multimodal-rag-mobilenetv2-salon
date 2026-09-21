import type { Metadata } from 'next';

import { ResourceManager } from '@/components/admin/resource-manager';

export const metadata: Metadata = {
  title: 'Kelola Users',
};

export default function AdminUsersPage() {
  return <ResourceManager resource="users" />;
}
