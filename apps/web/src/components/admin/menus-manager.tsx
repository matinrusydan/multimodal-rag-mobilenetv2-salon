'use client';

import { Folder, Pencil, Plus, Trash2 } from 'lucide-react';
import { Fragment, useCallback, useEffect, useMemo, useState } from 'react';
import type React from 'react';

import { Button } from '@/components/ui/button';
import { IconPicker } from '@/components/ui/icon-picker';
import { InputNumber } from '@/components/ui/input-number';
import { LoadingSpinner } from '@/components/ui/loading-spinner';
import { Modal } from '@/components/ui/modal';
import { Select } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Tag } from '@/components/ui/tag';
import { getAdminIcon } from '@/lib/admin-icons';
import { adminApi, type MenuItem, type RoleItem, type RouteItem } from '@/lib/admin-api';

interface FormState {
  name: string;
  path: string;
  icon: string;
  parentId: string;
  sortOrder: number;
  status: string;
  roleIds: string[];
}

const EMPTY: FormState = {
  name: '',
  path: '',
  icon: '',
  parentId: '',
  sortOrder: 1,
  status: 'active',
  roleIds: [],
};

export function MenusManager() {
  const [rows, setRows] = useState<MenuItem[]>([]);
  const [routes, setRoutes] = useState<RouteItem[]>([]);
  const [roles, setRoles] = useState<RoleItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  const [open, setOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<FormState>(EMPTY);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      const [menuList, routeList, roleList] = await Promise.all([
        adminApi.list<MenuItem>('menus'),
        adminApi.list<RouteItem>('routes'),
        adminApi.list<RoleItem>('roles'),
      ]);
      setRows(menuList);
      setRoutes(routeList);
      setRoles(roleList);
      setError('');
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const parents = useMemo(() => rows.filter((r) => !r.parentId), [rows]);
  const childrenOf = useCallback(
    (parentId: number) => rows.filter((r) => r.parentId === parentId),
    [rows],
  );

  const roleOptions = roles.map((r) => ({ value: String(r.id), label: `${r.name} (${r.code})` }));
  const routeOptions = routes.map((r) => ({
    value: r.path,
    label: `${r.title || r.name} — ${r.path}`,
  }));
  const parentOptions = parents.map((p) => ({ value: String(p.id), label: p.name }));

  const openAddGroup = () => {
    setEditingId(null);
    setForm({ ...EMPTY, parentId: '__none__', sortOrder: parents.length + 1 });
    setOpen(true);
  };

  // Tambah item di bawah parent tertentu (grup=level0, atau parent menu=level1).
  const openAddUnder = (parent: MenuItem) => {
    setEditingId(null);
    setForm({ ...EMPTY, parentId: String(parent.id), sortOrder: childrenOf(parent.id).length + 1 });
    setOpen(true);
  };

  const openEdit = (m: MenuItem) => {
    setEditingId(m.id);
    setForm({
      name: m.name,
      path: m.path,
      icon: m.icon ?? '',
      parentId: m.parentId ? String(m.parentId) : '__none__',
      sortOrder: m.sortOrder,
      status: m.status,
      roleIds: (m.roleIds ?? []).map(String),
    });
    setOpen(true);
  };

  const handleSave = async () => {
    setSaving(true);
    setError('');
    try {
      const hasParent = form.parentId && form.parentId !== '__none__';
      const payload: Record<string, unknown> = {
        name: form.name,
        // menu tanpa parent (group) -> path '#'
        path: hasParent ? form.path || '#' : '#',
        icon: form.icon || null,
        parentId: hasParent ? Number(form.parentId) : null,
        sortOrder: form.sortOrder,
        status: form.status,
        roleIds: form.roleIds.map(Number),
      };
      if (editingId === null) {
        await adminApi.create('menus', payload);
      } else {
        await adminApi.update('menus', editingId, payload);
      }
      setOpen(false);
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (m: MenuItem) => {
    if (!window.confirm(`Hapus menu ${m.name}?`)) return;
    try {
      await adminApi.remove('menus', m.id);
      await load();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const toggleExpand = (id: number) => {
    setExpanded((cur) => {
      const next = new Set(cur);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  if (loading) return <LoadingSpinner label="Memuat data..." />;

  // level: 0=Grup (judul), 1=Item/Parent, 2=Children (leaf).
  const renderRow = (m: MenuItem, level: number): React.ReactNode => {
    const kids = childrenOf(m.id);
    const hasKids = kids.length > 0;
    const isOpen = expanded.has(m.id);
    const isGroup = level === 0;
    const canAddChild = level < 2;

    return (
      <Fragment key={m.id}>
        <tr className={isGroup ? 'admin-tree-group-row' : undefined}>
          <td>
            <span style={{ paddingLeft: `${level * 1.5}rem` }}>
              {canAddChild && hasKids ? (
                <button
                  type="button"
                  className="admin-tree-toggle"
                  onClick={() => toggleExpand(m.id)}
                  aria-label={isOpen ? 'Tutup' : 'Buka'}
                >
                  {isOpen ? '−' : '+'}
                </button>
              ) : (
                <span className="admin-tree-toggle" style={{ visibility: 'hidden' }} />
              )}
              {isGroup ? (
                <span className="admin-tree-group-name">{m.name}</span>
              ) : (
                <>
                  <Folder size={15} style={{ display: 'inline', verticalAlign: 'middle' }} />{' '}
                  {m.name}
                </>
              )}
            </span>
          </td>
          <td>
            {m.icon ? (
              <span className="admin-iconcell">
                {(() => {
                  const I = getAdminIcon(m.icon);
                  return <I size={15} />;
                })()}
                <Tag tone="slate">{m.icon}</Tag>
              </span>
            ) : (
              '-'
            )}
          </td>
          <td>
            <code>{m.path}</code>
          </td>
          <td>
            <Tag tone={m.status === 'active' ? 'green' : 'red'}>
              {m.status === 'active' ? 'Aktif' : 'Nonaktif'}
            </Tag>
          </td>
          <td>
            <div className="admin-table__actions">
              {canAddChild ? (
                <button
                  type="button"
                  className="admin-icon-btn admin-icon-btn--primary"
                  onClick={() => openAddUnder(m)}
                  title={isGroup ? 'Tambah item ke grup' : 'Tambah sub-menu'}
                  aria-label="Tambah"
                >
                  <Plus size={14} />
                </button>
              ) : null}
              <button
                type="button"
                className="admin-icon-btn"
                onClick={() => openEdit(m)}
                aria-label="Edit"
              >
                <Pencil size={14} />
              </button>
              <button
                type="button"
                className="admin-icon-btn admin-icon-btn--danger"
                onClick={() => void handleDelete(m)}
                aria-label="Hapus"
              >
                <Trash2 size={14} />
              </button>
            </div>
          </td>
        </tr>
        {canAddChild && hasKids && isOpen ? kids.map((k) => renderRow(k, level + 1)) : null}
      </Fragment>
    );
  };

  const modalTitle =
    editingId !== null
      ? 'Edit Menu'
      : form.parentId && form.parentId !== '__none__'
        ? 'Tambah Menu'
        : 'Tambah Grup';

  return (
    <section className="admin-panel">
      <div className="admin-panel__toolbar">
        <h1>Menus</h1>
        <div className="admin-panel__toolbar-actions">
          <Button size="sm" onClick={openAddGroup}>
            <Plus size={16} /> Tambah Grup
          </Button>
        </div>
      </div>
      {error ? <p className="text-red-500 text-sm font-semibold">{error}</p> : null}
      <div className="admin-table">
        <table>
          <thead>
            <tr>
              <th>Title</th>
              <th>Icon</th>
              <th>Route</th>
              <th>Status</th>
              <th>Aksi</th>
            </tr>
          </thead>
          <tbody>
            {parents.map((p) => renderRow(p, 0))}
            {parents.length === 0 ? (
              <tr>
                <td colSpan={5} className="admin-table__empty">
                  Belum ada menu.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      <Modal
        open={open}
        onOpenChange={setOpen}
        title={modalTitle}
        footer={
          <>
            <Button variant="outline" size="sm" onClick={() => setOpen(false)}>
              Batal
            </Button>
            <Button size="sm" onClick={() => void handleSave()} disabled={saving}>
              {saving ? 'Menyimpan...' : 'Simpan'}
            </Button>
          </>
        }
      >
        <div className="admin-form">
          <div className="admin-form__field">
            <span>Parent</span>
            <Select
              value={form.parentId}
              onValueChange={(v) =>
                setForm({ ...form, parentId: v, path: v ? form.path : form.path })
              }
              options={[
                { value: '__none__', label: '(Tanpa Parent / menjadi Parent)' },
                ...parentOptions.filter((o) => o.value !== String(editingId ?? '')),
              ]}
              placeholder="Pilih parent"
            />
          </div>
          <label className="admin-form__field">
            <span>Title</span>
            <input
              type="text"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="mis. Master Data"
            />
          </label>
          <div className="admin-form__field">
            <span>Icon</span>
            <IconPicker
              value={form.icon}
              onValueChange={(v) => setForm({ ...form, icon: v })}
              placeholder="Pilih icon"
            />
          </div>
          {form.parentId && form.parentId !== '__none__' ? (
            <div className="admin-form__field admin-form__field--full">
              <span>Route</span>
              <Select
                value={form.path}
                onValueChange={(v) => setForm({ ...form, path: v })}
                options={routeOptions}
                placeholder="Pilih route"
              />
            </div>
          ) : null}
          <div className="admin-form__field">
            <span>Weight / Order</span>
            <InputNumber
              value={form.sortOrder}
              onChange={(v) => setForm({ ...form, sortOrder: v })}
              min={1}
              max={100}
            />
          </div>
          <div className="admin-form__field">
            <span>Status</span>
            <Switch
              checked={form.status === 'active'}
              onCheckedChange={(c) => setForm({ ...form, status: c ? 'active' : 'inactive' })}
              onLabel="Aktif"
              offLabel="Nonaktif"
            />
          </div>
          <div className="admin-form__field admin-form__field--full">
            <span>Akses Role</span>
            <div className="admin-perm-card__list" style={{ maxHeight: '10rem' }}>
              {roleOptions.map((r) => {
                const active = form.roleIds.includes(r.value);
                return (
                  <label key={r.value} className="admin-perm-item">
                    <input
                      type="checkbox"
                      checked={active}
                      onChange={() =>
                        setForm({
                          ...form,
                          roleIds: active
                            ? form.roleIds.filter((x) => x !== r.value)
                            : [...form.roleIds, r.value],
                        })
                      }
                    />
                    <span>{r.label}</span>
                  </label>
                );
              })}
            </div>
          </div>
        </div>
      </Modal>
    </section>
  );
}
