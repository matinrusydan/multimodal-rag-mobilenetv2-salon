import type { Metadata } from 'next';
import Link from 'next/link';

import { ALL_RESOURCES } from '@/components/admin/specs';

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
      <div className="admin-dashboard-grid">
        {ALL_RESOURCES.map((resource) => (
          <Link
            key={resource.resource}
            href={`/admin/${resource.resource}`}
            className="admin-dashboard-card"
          >
            <h2>{resource.resource}</h2>
            <p>Kelola data {resource.singular}</p>
          </Link>
        ))}
      </div>
    </section>
  );
}
