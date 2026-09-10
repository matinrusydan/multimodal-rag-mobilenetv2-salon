import Link from 'next/link';

const LINKS = [
  { href: '/admin', label: 'Ringkasan' },
  { href: '/admin/users', label: 'Users' },
  { href: '/admin/roles', label: 'Roles' },
  { href: '/admin/permissions', label: 'Permissions' },
  { href: '/admin/routes', label: 'Routes' },
  { href: '/admin/menus', label: 'Menus' },
];

export function AdminNav() {
  return (
    <nav className="admin-nav" aria-label="Navigasi admin">
      {LINKS.map((link) => (
        <Link key={link.href} href={link.href} className="admin-nav__link">
          {link.label}
        </Link>
      ))}
    </nav>
  );
}
