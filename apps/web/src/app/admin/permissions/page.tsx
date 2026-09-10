import type { Metadata } from 'next';

import { ResourceManager } from '@/components/admin/resource-manager';
import { permissionResource } from '@/components/admin/specs';

export const metadata: Metadata = {
  title: 'Kelola Permissions',
};

export default function AdminPermissionsPage() {
  return <ResourceManager spec={permissionResource} />;
}
