'use client';

import { ChevronLeft, ChevronRight, ChevronDown, LogOut, Scissors } from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import type React from 'react';
import { useCallback, useEffect, useMemo, useState } from 'react';

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

const STORAGE_KEY = 'adminSidebarCollapsed';

function isActive(pathname: string, path: string): boolean {
  if (path === '/admin') return pathname === '/admin';
  if (!path || path === '#') return false;
  return pathname === path || pathname.startsWith(`${path}/`);
}

export function AdminSidebar() {
  const pathname = usePathname();
  const { user, isReady, logout } = useAuth();

  // State terisolasi per komponen berbasis useState
  const [menus, setMenus] = useState<MenuItem[]>([]);
  const [menusUserId, setMenusUserId] = useState<number | null>(null);
  const [menuState, setMenuState] = useState<'loading' | 'error' | 'ready'>('loading');
  const [retry, setRetry] = useState(0);
  const [collapsed, setCollapsed] = useState(false);
  const [openGroups, setOpenGroups] = useState<Set<number>>(() => new Set());

  // Sinkronisasi status collapsed dari localStorage tanpa re-render berlebih jika false
  useEffect(() => {
    try {
      if (localStorage.getItem(STORAGE_KEY) === '1') {
        setCollapsed(true);
      }
    } catch {
      /* ignore */
    }
  }, []);

  // Fetch menu per user dengan abort controller & penanganan isReady
  useEffect(() => {
    if (!isReady) return;

    if (!user) {
      setMenus([]);
      setMenusUserId(null);
      setMenuState('ready');
      return;
    }

    const controller = new AbortController();
    setMenuState('loading');

    fetch('/api/admin/menus/me', { cache: 'no-store', signal: controller.signal })
      .then(async (res) => {
        if (!res.ok) throw new Error('Menu request failed');
        return (await res.json()) as { data?: MenuItem[] };
      })
      .then((body) => {
        if (controller.signal.aborted) return;
        const all = body.data ?? [];
        setMenus(all.filter((menu) => menu.path.startsWith('/admin') || menu.path === '#'));
        setMenusUserId(user.id);
        setMenuState('ready');
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setMenus([]);
          setMenusUserId(null);
          setMenuState('error');
        }
      });

    return () => controller.abort();
  }, [user?.id, isReady, retry]);

  const visibleMenus = user?.id === menusUserId ? menus : [];

  // 1. Pembuatan tree & map dalam satu kali iterasi O(N) ter-memoize
  const { roots, childrenOf, menuMap } = useMemo(() => {
    const rootsList: MenuItem[] = [];
    const childrenMap = new Map<number, MenuItem[]>();
    const nodeMap = new Map<number, MenuItem>();

    for (const m of visibleMenus) {
      nodeMap.set(m.id, m);
      if (!m.parentId) {
        rootsList.push(m);
      } else {
        const arr = childrenMap.get(m.parentId) ?? [];
        arr.push(m);
        childrenMap.set(m.parentId, arr);
      }
    }

    rootsList.sort((a, b) => a.sortOrder - b.sortOrder);
    for (const arr of childrenMap.values()) {
      arr.sort((a, b) => a.sortOrder - b.sortOrder);
    }

    return { roots: rootsList, childrenOf: childrenMap, menuMap: nodeMap };
  }, [visibleMenus]);

  // 2. Pre-kalkulasi ID aktif O(N) - menggantikan pencarian rekursif O(N^2) di dalam render
  const activeMenuIds = useMemo(() => {
    const set = new Set<number>();
    if (!pathname || visibleMenus.length === 0) return set;

    for (const m of visibleMenus) {
      if (isActive(pathname, m.path)) {
        set.add(m.id);
        let parentId = m.parentId;
        while (parentId !== null) {
          set.add(parentId);
          const parent = menuMap.get(parentId);
          parentId = parent?.parentId ?? null;
        }
      }
    }
    return set;
  }, [pathname, visibleMenus, menuMap]);

  // 3. Callback stabil via useCallback
  const toggleCollapsed = useCallback(() => {
    setCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem(STORAGE_KEY, next ? '1' : '0');
      } catch {
        /* ignore */
      }
      return next;
    });
  }, []);

  const toggleGroup = useCallback((id: number) => {
    setOpenGroups((cur) => {
      const next = new Set(cur);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const handleRetry = useCallback(() => {
    setRetry((count) => count + 1);
  }, []);

  // 4. Render node teroptimasi O(1) per pemeriksaan aktif
  const renderNode = (menu: MenuItem, level: number): React.ReactNode => {
    const kids = childrenOf.get(menu.id) ?? [];
    const hasKids = kids.length > 0;
    const hasIcon = Boolean(menu.icon);
    const indent = level > 0;

    // Leaf: link
    if (!hasKids) {
      if (!hasIcon && (!menu.path || menu.path === '#')) {
        if (collapsed) return null;
        return (
          <div key={menu.id} className="admin-sidebar__group-title" title={menu.name}>
            {menu.name}
          </div>
        );
      }
      const Icon = getAdminIcon(menu.icon);
      const active = isActive(pathname, menu.path);
      return (
        <Link
          key={menu.id}
          href={menu.path}
          className={cn(
            'admin-sidebar__link',
            indent && 'admin-sidebar__link--child',
            active && 'admin-sidebar__link--active',
          )}
          title={collapsed ? menu.name : undefined}
        >
          <Icon size={indent ? 16 : 18} />
          <span>{menu.name}</span>
        </Link>
      );
    }

    // Level-0 tanpa icon -> judul grup statis
    if (!hasIcon && level === 0) {
      return (
        <div key={menu.id} className="admin-sidebar__section">
          {!collapsed ? (
            <div className="admin-sidebar__group-title" title={menu.name}>
              {menu.name}
            </div>
          ) : null}
          <div className="admin-sidebar__children admin-sidebar__children--flat">
            {kids.map((k) => renderNode(k, level + 1))}
          </div>
        </div>
      );
    }

    // Parent dropdown / accordion
    const Icon = menu.icon ? getAdminIcon(menu.icon) : null;
    const open = openGroups.has(menu.id);
    const groupActive = activeMenuIds.has(menu.id);

    return (
      <div key={menu.id} className="admin-sidebar__group">
        <button
          type="button"
          className={cn(
            'admin-sidebar__link admin-sidebar__link--group',
            indent && 'admin-sidebar__link--child',
            groupActive && 'admin-sidebar__link--group-active',
          )}
          onClick={() => toggleGroup(menu.id)}
          title={collapsed ? menu.name : undefined}
        >
          {Icon ? <Icon size={indent ? 16 : 18} /> : null}
          <span>{menu.name}</span>
          {!collapsed ? (
            <ChevronDown size={14} className="admin-sidebar__caret" data-open={open} />
          ) : null}
        </button>
        {open && !collapsed ? (
          <div className="admin-sidebar__children">{kids.map((k) => renderNode(k, level + 1))}</div>
        ) : null}
      </div>
    );
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
        {menuState === 'loading' ? <p role="status">Memuat menu...</p> : null}
        {menuState === 'error' ? (
          <div role="alert">
            <p>Menu gagal dimuat.</p>
            <button type="button" onClick={handleRetry}>
              Coba lagi
            </button>
          </div>
        ) : null}
        {menuState === 'ready' && user && roots.length === 0 ? (
          <p>Belum ada menu yang tersedia.</p>
        ) : null}
        {roots.map((menu) => renderNode(menu, 0))}
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

