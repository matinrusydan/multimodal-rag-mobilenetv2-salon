'use client';

import { useEffect, useState } from 'react';

import { LoadingSpinner } from '@/components/ui/loading-spinner';
import { Tag } from '@/components/ui/tag';
import { adminApi, type MenuItem, type RoleItem } from '@/lib/admin-api';

const ROLE_TONES = ['blue', 'cyan', 'green', 'magenta', 'slate'] as const;

export function RoleMenusMatrix() {
  const [menus, setMenus] = useState<MenuItem[]>([]);
  const [roles, setRoles] = useState<RoleItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState<number | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const [menuList, roleList] = await Promise.all([
        adminApi.list<MenuItem>('menus'),
        adminApi.list<RoleItem>('roles'),
      ]);
      setMenus(menuList);
      setRoles(roleList);
      setError('');
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const toggle = async (menu: MenuItem, roleId: number) => {
    const has = (menu.roleIds ?? []).includes(roleId);
    const next = has
      ? (menu.roleIds ?? []).filter((r) => r !== roleId)
      : [...(menu.roleIds ?? []), roleId];
    setSaving(menu.id);
    try {
      await fetch(`/api/admin/menus/${menu.id}/roles`, {
        method: 'PUT',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ roleIds: next }),
      });
      setMenus((cur) => cur.map((m) => (m.id === menu.id ? { ...m, roleIds: next } : m)));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(null);
    }
  };

  if (loading) return <LoadingSpinner label="Memuat data..." />;

  return (
    <section className="admin-panel">
      <div className="admin-panel__toolbar">
        <h1>Akses Menu per Role</h1>
      </div>
      <p className="muted-text">
        Centang untuk memberi role akses ke menu. Ini mengatur <strong>tampilnya menu</strong>,
        terpisah dari permission.
      </p>
      {error ? <p className="text-red-500 text-sm font-semibold">{error}</p> : null}

      <div className="admin-matrix">
        <table>
          <thead>
            <tr>
              <th>Menu</th>
              <th>Path</th>
              {roles.map((r, i) => (
                <th key={r.id}>
                  <Tag tone={ROLE_TONES[i % ROLE_TONES.length]}>{r.code}</Tag>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {menus.map((m) => (
              <tr key={m.id}>
                <td>{m.name}</td>
                <td>
                  <code>{m.path}</code>
                </td>
                {roles.map((r) => {
                  const checked = (m.roleIds ?? []).includes(r.id);
                  return (
                    <td key={r.id}>
                      <input
                        type="checkbox"
                        checked={checked}
                        disabled={saving === m.id}
                        aria-label={`${m.name} - ${r.code}`}
                        onChange={() => void toggle(m, r.id)}
                      />
                    </td>
                  );
                })}
              </tr>
            ))}
            {menus.length === 0 ? (
              <tr>
                <td colSpan={roles.length + 2} className="admin-table__empty">
                  Belum ada menu.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </section>
  );
}
