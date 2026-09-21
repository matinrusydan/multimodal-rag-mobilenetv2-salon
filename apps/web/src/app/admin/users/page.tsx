import type { Metadata } from 'next';

import { UsersManager } from '@/components/admin/users-manager';

export const metadata: Metadata = {
  title: 'Kelola Pengguna',
};

export default function AdminUsersPage() {
  return <UsersManager />;
}
