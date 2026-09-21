'use client';

import { Pencil, Plus, Trash2 } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';

import { Button } from '@/components/ui/button';
import { LoadingSpinner } from '@/components/ui/loading-spinner';
import { Modal } from '@/components/ui/modal';
import { MultiSelect } from '@/components/ui/multiselect';
import { Select } from '@/components/ui/select';
import { Tag } from '@/components/ui/tag';
import { adminApi, type RoleItem, type RouteItem } from '@/lib/admin-api';

interface FormState {
  name: string;
  title: string;
  path: string;
  parentId: string;
  status: string;
  roleIds: string[];
}

const EMPTY: FormState = {
  name: '',
  title: '',
  path: '',
  parentId: '',
  status: 'active',
  roleIds: [],
};

export function RoutesManager() {
  const [rows, setRows] = useState<RouteItem[]>([]);
  const [roles, setRoles] = useState<RoleItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [open, setOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<FormState>(EMPTY);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      const [routeList, roleList] = await Promise.all([
        adminApi.list<RouteItem>('routes'),
        adminApi.list<RoleItem>('roles'),
      ]);
      setRows(routeList);
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

  const roleOptions = roles.map((r) => ({ value: String(r.id), label: `${r.name} (${r.code})` }));
  const parentOptions = rows.map((r) => ({ value: String(r.id), label: r.title || r.path }));

  const openCreate = () => {
    setEditingId(null);
    setForm(EMPTY);
    setOpen(true);
  };

  const openEdit = (r: RouteItem) => {
    setEditingId(r.id);
    setForm({
      name: r.name,
      title: r.title ?? '',
      path: r.path,
      parentId: r.parentId ? String(r.parentId) : '',
      status: r.status,
      roleIds: (r.roleIds ?? []).map(String),
    });
    setOpen(true);
  };

  const handleSave = async () => {
    setSaving(true);
    setError('');
    try {
      const payload: Record<string, unknown> = {
        name: form.name,
        title: form.title || null,
        path: form.path,
        parentId: form.parentId ? Number(form.parentId) : null,
        status: form.status,
      };
      let saved: RouteItem;
      if (editingId === null) {
        saved = await adminApi.create<RouteItem>('routes', payload);
      } else {
        saved = await adminApi.update<RouteItem>('routes', editingId, payload);
      }
      if (form.roleIds.length) {
        await fetch(`/api/admin/routes/${saved.id}/roles`, {
          method: 'PUT',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({ roleIds: form.roleIds.map(Number) }),
        });
      }
      setOpen(false);
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (r: RouteItem) => {
    if (!window.confirm(`Hapus route ${r.path}?`)) return;
    try {
      await adminApi.remove('routes', r.id);
      await load();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  if (loading) return <LoadingSpinner label="Memuat data..." />;

  return (
    <section className="admin-panel">
      <div className="admin-panel__toolbar">
        <h1>Routes</h1>
        <div className="admin-panel__toolbar-actions">
          <Button size="sm" onClick={openCreate}>
            <Plus size={16} /> Tambah Route
          </Button>
        </div>
      </div>
      {error ? <p className="text-red-500 text-sm font-semibold">{error}</p> : null}
      <div className="admin-table">
        <table>
          <thead>
            <tr>
              <th>Nama</th>
              <th>Path</th>
              <th>Title</th>
              <th>Status</th>
              <th>Akses Role</th>
              <th>Aksi</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td>{r.name}</td>
                <td>
                  <code>{r.path}</code>
                </td>
                <td>{r.title ?? '-'}</td>
                <td>
                  <Tag tone={r.status === 'active' ? 'green' : 'red'}>
                    {r.status === 'active' ? 'Aktif' : 'Nonaktif'}
                  </Tag>
                </td>
                <td>
                  {(r.roleIds ?? []).length
                    ? (r.roleIds ?? [])
                        .map((id) => roles.find((ro) => ro.id === id)?.code ?? `#${id}`)
                        .map((c) => (
                          <Tag key={c} tone="cyan">
                            {c}
                          </Tag>
                        ))
                    : '-'}
                </td>
                <td>
                  <div className="admin-table__actions">
                    <button
                      type="button"
                      className="admin-icon-btn"
                      onClick={() => openEdit(r)}
                      aria-label="Edit"
                    >
                      <Pencil size={14} />
                    </button>
                    <button
                      type="button"
                      className="admin-icon-btn admin-icon-btn--danger"
                      onClick={() => void handleDelete(r)}
                      aria-label="Hapus"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {rows.length === 0 ? (
              <tr>
                <td colSpan={6} className="admin-table__empty">
                  Belum ada route.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      <Modal
        open={open}
        onOpenChange={setOpen}
        title={editingId === null ? 'Tambah Route' : 'Edit Route'}
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
          <label className="admin-form__field">
            <span>Nama Route</span>
            <input
              type="text"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="mis. Kelola Pengguna"
            />
          </label>
          <label className="admin-form__field">
            <span>Path</span>
            <input
              type="text"
              value={form.path}
              onChange={(e) => setForm({ ...form, path: e.target.value })}
              placeholder="mis. /admin/users"
            />
          </label>
          <label className="admin-form__field">
            <span>Title</span>
            <input
              type="text"
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              placeholder="Judul route"
            />
          </label>
          <div className="admin-form__field">
            <span>Parent</span>
            <Select
              value={form.parentId}
              onValueChange={(v) => setForm({ ...form, parentId: v })}
              options={parentOptions}
              placeholder="(Tanpa parent)"
            />
          </div>
          <div className="admin-form__field admin-form__field--full">
            <span>Dapat Diakses Role</span>
            <MultiSelect
              values={form.roleIds}
              options={roleOptions}
              onChange={(v) => setForm({ ...form, roleIds: v })}
              placeholder="Pilih role..."
            />
          </div>
          <div className="admin-form__field">
            <span>Status</span>
            <Select
              value={form.status}
              onValueChange={(v) => setForm({ ...form, status: v })}
              options={[
                { value: 'active', label: 'Aktif' },
                { value: 'inactive', label: 'Nonaktif' },
              ]}
            />
          </div>
        </div>
      </Modal>
    </section>
  );
}
