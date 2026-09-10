import type { Metadata } from 'next';

import { ResourceManager } from '@/components/admin/resource-manager';
import { userResource } from '@/components/admin/specs';

export const metadata: Metadata = {
  title: 'Kelola Users',
};

export default function AdminUsersPage() {
  return <ResourceManager spec={userResource} />;
}
