'use client';

import { ChevronLeft, ChevronRight, ChevronDown, LogOut, Scissors } from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';

import { getAdminIcon } from '@/lib/admin-icons';
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

const FALLBACK: MenuItem[] = [
  { id: -2, name: 'Kelola Pengguna', path: '/admin/users', icon: 'users', parentId: null, sortOrder: 10 },
  { id: -3, name: 'Kelola Role', path: '/admin/roles', icon: 'shield', parentId: null, sortOrder: 11 },
  { id: -4, name: 'Permissions', path: '/admin/permissions', icon: 'key', parentId: null, sortOrder: 12 },
  { id: -5, name: 'Routes', path: '/admin/routes', icon: 'route', parentId: null, sortOrder: 13 },
  { id: -6, name: 'Menus', path: '/admin/menus', icon: 'list', parentId: null, sortOrder: 14 },
  { id: -7, name: 'Akses Menu', path: '/admin/role-menus', icon: 'shield', parentId: null, sortOrder: 15 },
];

const STORAGE_KEY = 'adminSidebarCollapsed';

function isActive(pathname: string, path: string): boolean {
  if (path === '/admin') return pathname === '/admin';
  if (!path || path === '#') return false;
  return pathname === path || pathname.startsWith(`${path}/`);
}

export function AdminSidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const [menus, setMenus] = useState<MenuItem[]>([]);
  const [collapsed, setCollapsed] = useState(false);
  const [openGroups, setOpenGroups] = useState<Set<number>>(new Set());

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
        const adminMenus = all.filter((m) => m.path.startsWith('/admin') || m.path === '#');
        setMenus(adminMenus.length > 0 ? adminMenus : FALLBACK);
      })
      .catch(() => setMenus(FALLBACK));
    return () => {
      cancelled = true;
    };
  }, []);

  const { roots, childrenOf } = useMemo(() => {
    const roots = menus.filter((m) => !m.parentId);
    const map = new Map<number, MenuItem[]>();
    for (const m of menus) {
      if (m.parentId) {
        const arr = map.get(m.parentId) ?? [];
        arr.push(m);
        map.set(m.parentId, arr);
      }
    }
    for (const arr of map.values()) arr.sort((a, b) => a.sortOrder - b.sortOrder);
    return { roots: roots.sort((a, b) => a.sortOrder - b.sortOrder), childrenOf: map };
  }, [menus]);

  // Buka grup yang berisi path aktif.
  useEffect(() => {
    const open = new Set<number>();
    for (const r of roots) {
      const kids = childrenOf.get(r.id) ?? [];
      if (kids.some((k) => isActive(pathname, k.path))) open.add(r.id);
    }
    setOpenGroups(open);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname, menus]);

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

  const toggleGroup = (id: number) => {
    setOpenGroups((cur) => {
      const next = new Set(cur);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <aside
      className={cn('admin-sidebar', collapsed && 'admin-sidebar--collapsed')}
      aria-label="Navigasi admin"
    >
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
        {roots.map((menu) => {
          const kids = (childrenOf.get(menu.id) ?? []).filter((k) => k.path !== '#');
          const isSubmenu = kids.length > 0;
          const hasIcon = Boolean(menu.icon);

          // 1) Grup berjudul (root tanpa icon, punya children) -> judul + children flat.
          if (isSubmenu && !hasIcon) {
            return (
              <div key={menu.id} className="admin-sidebar__section">
                {!collapsed ? (
                  <div className="admin-sidebar__group-title" title={menu.name}>
                    {menu.name}
                  </div>
                ) : null}
                <div className="admin-sidebar__children admin-sidebar__children--flat">
                  {kids.map((k) => {
                    const KIcon = getAdminIcon(k.icon);
                    const active = isActive(pathname, k.path);
                    return (
                      <Link
                        key={k.id}
                        href={k.path}
                        className={cn(
                          'admin-sidebar__link admin-sidebar__link--child',
                          active && 'admin-sidebar__link--active',
                        )}
                        title={collapsed ? k.name : undefined}
                      >
                        <KIcon size={16} />
                        <span>{k.name}</span>
                      </Link>
                    );
                  })}
                </div>
              </div>
            );
          }

          // 2) Judul grup murni (root tanpa children & tanpa icon).
          if (!isSubmenu && !hasIcon) {
            if (collapsed) return null;
            return (
              <div key={menu.id} className="admin-sidebar__group-title" title={menu.name}>
                {menu.name}
              </div>
            );
          }

          // 3) Submenu (root dengan icon & children) -> accordion.
          if (isSubmenu) {
            const open = openGroups.has(menu.id);
            const groupActive = kids.some((k) => isActive(pathname, k.path));
            const Icon = getAdminIcon(menu.icon);
            return (
              <div key={menu.id} className="admin-sidebar__group">
                <button
                  type="button"
                  className={cn(
                    'admin-sidebar__link admin-sidebar__link--group',
                    groupActive && 'admin-sidebar__link--group-active',
                  )}
                  onClick={() => toggleGroup(menu.id)}
                  title={collapsed ? menu.name : undefined}
                >
                  <Icon size={18} />
                  <span>{menu.name}</span>
                  {!collapsed ? (
                    <ChevronDown size={14} className="admin-sidebar__caret" data-open={open} />
                  ) : null}
                </button>
                {open && !collapsed ? (
                  <div className="admin-sidebar__children">
                    {kids.map((k) => {
                      const KIcon = getAdminIcon(k.icon);
                      const active = isActive(pathname, k.path);
                      return (
                        <Link
                          key={k.id}
                          href={k.path}
                          className={cn(
                            'admin-sidebar__link admin-sidebar__link--child',
                            active && 'admin-sidebar__link--active',
                          )}
                        >
                          <KIcon size={16} />
                          <span>{k.name}</span>
                        </Link>
                      );
                    })}
                  </div>
                ) : null}
              </div>
            );
          }

          // 4) Item tunggal (root dengan path/icon, tanpa children).
          const active = isActive(pathname, menu.path);
          const Icon = getAdminIcon(menu.icon);
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
        <span>Tutup</span>
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
