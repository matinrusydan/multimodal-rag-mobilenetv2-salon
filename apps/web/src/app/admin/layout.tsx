import { redirect } from 'next/navigation';
import type React from 'react';

import { AdminAgentWidget } from '@/components/admin/admin-agent-widget';
import { AdminSidebar } from '@/components/admin/admin-sidebar';
import { getSession } from '@/lib/web-session';

const ADMIN_RESOURCES = ['users', 'roles', 'permissions', 'routes', 'menus'] as const;

export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  const session = await getSession();
  const user = session?.user;
  if (!user) {
    redirect('/auth');
  }

  const canAdmin =
    user.type === 0 ||
    ADMIN_RESOURCES.some((resource) => user.permissions.includes(`${resource}.read`));
  if (!canAdmin) {
    redirect('/home');
  }

  return (
    <div className="admin-shell">
      <AdminSidebar />
      <main className="admin-main">
        <div className="site-container">{children}</div>
      </main>
      <AdminAgentWidget />
    </div>
  );
}

