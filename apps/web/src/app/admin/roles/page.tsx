import type { Metadata } from 'next';

import { ResourceManager } from '@/components/admin/resource-manager';
import { roleResource } from '@/components/admin/specs';

export const metadata: Metadata = {
  title: 'Kelola Roles',
};

export default function AdminRolesPage() {
  return <ResourceManager spec={roleResource} />;
}
