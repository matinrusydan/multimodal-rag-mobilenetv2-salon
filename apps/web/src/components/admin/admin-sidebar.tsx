'use client';

import {
  CalendarCheck,
  ChevronLeft,
  ChevronRight,
  CreditCard,
  Home,
  Key,
  LayoutDashboard,
  List,
  LogOut,
  type LucideIcon,
  Route as RouteIcon,
  Scissors,
  Shield,
  Sparkles,
  User,
  Users,
  Wallet,
} from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';

import { useAuth } from '@/lib/use-auth';
import { cn } from '@/lib/utils';

interface MenuItem {
  id: number;
  name: string;
  path: string;
  icon: string | null;
  parentId: number | null;
  sortOrder: number;
}

const ICONS: Record<string, LucideIcon> = {
  home: Home,
  scissors: Scissors,
  sparkles: Sparkles,
  calendar: CalendarCheck,
  wallet: Wallet,
  credit: CreditCard,
  users: Users,
  user: User,
  shield: Shield,
  key: Key,
  route: RouteIcon,
  list: List,
  dashboard: LayoutDashboard,
};

const FALLBACK: MenuItem[] = [
  { id: 0, name: 'Ringkasan', path: '/admin', icon: 'dashboard', parentId: null, sortOrder: 0 },
  { id: -2, name: 'Pengguna', path: '/admin/users', icon: 'users', parentId: null, sortOrder: 10 },
  { id: -3, name: 'Roles', path: '/admin/roles', icon: 'shield', parentId: null, sortOrder: 11 },
  { id: -4, name: 'Permissions', path: '/admin/permissions', icon: 'key', parentId: null, sortOrder: 12 },
  { id: -5, name: 'Routes', path: '/admin/routes', icon: 'route', parentId: null, sortOrder: 13 },
  { id: -6, name: 'Menus', path: '/admin/menus', icon: 'list', parentId: null, sortOrder: 14 },
];

const STORAGE_KEY = 'adminSidebarCollapsed';

function isActive(pathname: string, path: string): boolean {
  if (path === '/admin') return pathname === '/admin';
  return pathname === path || pathname.startsWith(`${path}/`);
}

export function AdminSidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const [menus, setMenus] = useState<MenuItem[]>([]);
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    try {
      setCollapsed(localStorage.getItem(STORAGE_KEY) === '1');
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    fetch('/api/admin/menus/me', { cache: 'no-store' })
      .then((res) => res.json())
      .then((body: { data?: MenuItem[] }) => {
        if (cancelled) return;
        const all = body.data ?? [];
        const adminMenus = all.filter((m) => m.path.startsWith('/admin'));
        setMenus([
          { id: 0, name: 'Ringkasan', path: '/admin', icon: 'dashboard', parentId: null, sortOrder: 0 },
          ...adminMenus,
        ]);
      })
      .catch(() => setMenus(FALLBACK));
    return () => {
      cancelled = true;
    };
  }, []);

  const toggleCollapsed = () => {
    setCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem(STORAGE_KEY, next ? '1' : '0');
      } catch {
        /* ignore */
      }
      return next;
    });
  };

  const items = menus;

  return (
    <aside className={cn('admin-sidebar', collapsed && 'admin-sidebar--collapsed')} aria-label="Navigasi admin">
      <div className="admin-sidebar__brand">
        <span className="admin-sidebar__logo">
          <Scissors size={18} />
        </span>
        <span className="admin-sidebar__brand-text">
          <strong>TIEN SALON</strong>
          <small>Admin Panel</small>
        </span>
      </div>

      <nav className="admin-sidebar__nav">
        {items.map((menu) => {
          const Icon = ICONS[menu.icon ?? ''] ?? LayoutDashboard;
          const active = isActive(pathname, menu.path);
          return (
            <Link
              key={menu.id}
              href={menu.path}
              className={cn('admin-sidebar__link', active && 'admin-sidebar__link--active')}
              title={collapsed ? menu.name : undefined}
            >
              <Icon size={18} />
              <span>{menu.name}</span>
            </Link>
          );
        })}
      </nav>

      <button
        type="button"
        className="admin-sidebar__collapse"
        onClick={toggleCollapsed}
        aria-label={collapsed ? 'Perluas sidebar' : 'Ciutkan sidebar'}
      >
        {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        <span>Ciutkan</span>
      </button>

      {user ? (
        <div className="admin-sidebar__user">
          <div className="admin-sidebar__user-info">
            <strong>{user.name}</strong>
            <small>{user.roles.join(', ') || 'user'}</small>
          </div>
          <button
            type="button"
            className="admin-sidebar__logout"
            onClick={() => void logout().then(() => (window.location.href = '/auth'))}
            aria-label="Keluar"
            title="Keluar"
          >
            <LogOut size={16} />
          </button>
        </div>
      ) : null}
    </aside>
  );
}
