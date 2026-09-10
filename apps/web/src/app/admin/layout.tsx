import { redirect } from 'next/navigation';
import type React from 'react';

import { AdminNav } from '@/components/admin/admin-nav';
import { getSession } from '@/lib/web-session';

const ADMIN_RESOURCES = ['users', 'roles', 'permissions', 'routes', 'menus'] as const;

export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  const session = await getSession();
  const user = session?.user;
  if (!user) {
    redirect('/login');
  }

  const canAdmin =
    user.type === 0 ||
    ADMIN_RESOURCES.some((resource) => user.permissions.includes(`${resource}.read`));
  if (!canAdmin) {
    redirect('/home');
  }

  return (
    <main className="site-section">
      <div className="site-container">
        <AdminNav />
        {children}
      </div>
    </main>
  );
}
