import type { Metadata } from 'next';
import Link from 'next/link';

import { AdminStats } from '@/components/admin/admin-stats';
import { RESOURCE_META } from '@/components/admin/resource-meta';

export const metadata: Metadata = {
  title: 'Dashboard Admin',
  description: 'Panel administrasi TIEN SALON untuk mengelola RBAC.',
};

export default function AdminDashboardPage() {
  return (
    <section className="admin-panel">
      <h1>Dashboard Admin</h1>
      <p className="muted-text">
        Kelola pengguna, role, permission, route, dan menu. Super admin: admin@rag-salon.id
        (Password123!).
      </p>

      <AdminStats />

      <h2 className="admin-panel__section-title">Kelola Data</h2>
      <div className="admin-dashboard-grid">
        {RESOURCE_META.map((resource) => (
          <Link
            key={resource.resource}
            href={`/admin/${resource.resource}`}
            className="admin-dashboard-card"
          >
            <h2>{resource.label}</h2>
            <p>Kelola data {resource.singular}</p>
          </Link>
        ))}
      </div>
    </section>
  );
}
