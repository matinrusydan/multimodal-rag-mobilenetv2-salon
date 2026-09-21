import type { Metadata } from 'next';

import { RoleMenusMatrix } from '@/components/admin/role-menus-matrix';

export const metadata: Metadata = {
  title: 'Akses Menu per Role',
};

export default function AdminRoleMenusPage() {
  return <RoleMenusMatrix />;
}
