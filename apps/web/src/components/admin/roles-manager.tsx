'use client';

import { Pencil, Plus, ShieldCheck, Trash2 } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';

import { Button } from '@/components/ui/button';
import { LoadingSpinner } from '@/components/ui/loading-spinner';
import { Modal } from '@/components/ui/modal';
import { Select } from '@/components/ui/select';
import { Tag } from '@/components/ui/tag';
import { adminApi } from '@/lib/admin-api';

interface PermissionItem {
  id: number;
  name: string;
  resource: string;
  description?: string;
}

interface RoleItem {
  id: number;
  name: string;
  code: string;
  type: number;
  status: string;
  description: string | null;
  permissions: string[];
}

interface FormState {
  name: string;
  code: string;
  group: string;
  status: string;
  description: string;
}

const EMPTY: FormState = { name: '', code: '', group: '', status: 'active', description: '' };

export function RolesManager() {
  const [rows, setRows] = useState<RoleItem[]>([]);
  const [permissions, setPermissions] = useState<PermissionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [open, setOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<FormState>(EMPTY);
  const [saving, setSaving] = useState(false);

  const [permOpen, setPermOpen] = useState(false);
  const [permRole, setPermRole] = useState<RoleItem | null>(null);
  const [selectedPerms, setSelectedPerms] = useState<number[]>([]);
  const [savingPerms, setSavingPerms] = useState(false);

  const load = useCallback(async () => {
    try {
      const [roleList, permList] = await Promise.all([
        adminApi.list<RoleItem>('roles'),
        adminApi.list<PermissionItem>('permissions'),
      ]);
      setRows(roleList);
      setPermissions(permList);
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

  const permByName = useMemo(() => new Map(permissions.map((p) => [p.name, p])), [permissions]);

  const openCreate = () => {
    setEditingId(null);
    setForm(EMPTY);
    setOpen(true);
  };

  const openEdit = (r: RoleItem) => {
    setEditingId(r.id);
    setForm({
      name: r.name,
      code: r.code,
      group: '',
      status: r.status,
      description: r.description ?? '',
    });
    setOpen(true);
  };

  const handleSave = async () => {
    setSaving(true);
    setError('');
    try {
      const payload: Record<string, unknown> = {
        name: form.name,
        code: form.code.trim().toUpperCase(),
        status: form.status,
        description: form.description || null,
      };
      if (editingId === null) {
        await adminApi.create('roles', payload);
      } else {
        await adminApi.update('roles', editingId, payload);
      }
      setOpen(false);
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (r: RoleItem) => {
    if (!window.confirm(`Hapus role ${r.name}?`)) return;
    try {
      await adminApi.remove('roles', r.id);
      await load();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const openPermissions = (r: RoleItem) => {
    setPermRole(r);
    setSelectedPerms(r.permissions.map((name) => permByName.get(name)?.id ?? -1).filter((x) => x > 0));
    setPermOpen(true);
  };

  const togglePerm = (id: number) => {
    setSelectedPerms((cur) => (cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id]));
  };

  const savePermissions = async () => {
    if (!permRole) return;
    setSavingPerms(true);
    try {
      await fetch(`/api/admin/roles/${permRole.id}/permissions`, {
        method: 'PUT',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ permissionIds: selectedPerms }),
      });
      setPermOpen(false);
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSavingPerms(false);
    }
  };

  // grup permission per resource
  const byResource = useMemo(() => {
    const map = new Map<string, PermissionItem[]>();
    for (const p of permissions) {
      const arr = map.get(p.resource) ?? [];
      arr.push(p);
      map.set(p.resource, arr);
    }
    return map;
  }, [permissions]);

  if (loading) return <LoadingSpinner label="Memuat data..." />;

  return (
    <section className="admin-panel">
      <div className="admin-panel__toolbar">
        <h1>Roles</h1>
        <div className="admin-panel__toolbar-actions">
          <Button size="sm" onClick={openCreate}>
            <Plus size={16} /> Tambah Role
          </Button>
        </div>
      </div>
      {error ? <p className="text-red-500 text-sm font-semibold">{error}</p> : null}
      <div className="admin-table">
        <table>
          <thead>
            <tr>
              <th>Nama</th>
              <th>Kode</th>
              <th>Deskripsi</th>
              <th>Status</th>
              <th>Permissions</th>
              <th>Aksi</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td>{r.name}</td>
                <td>
                  <Tag tone="blue">{r.code}</Tag>
                </td>
                <td>{r.description ?? '-'}</td>
                <td>
                  <Tag tone={r.status === 'active' ? 'green' : 'red'}>
                    {r.status === 'active' ? 'Aktif' : 'Nonaktif'}
                  </Tag>
                </td>
                <td>{r.permissions.length}</td>
                <td>
                  <div className="admin-table__actions">
                    <button
                      type="button"
                      className="admin-icon-btn"
                      title="Atur Permission"
                      onClick={() => openPermissions(r)}
                      aria-label="Atur permission"
                    >
                      <ShieldCheck size={14} />
                    </button>
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
                  Belum ada role.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      <Modal
        open={open}
        onOpenChange={setOpen}
        title={editingId === null ? 'Tambah Role' : 'Edit Role'}
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
            <span>Nama</span>
            <input
              type="text"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="mis. Administrator"
            />
          </label>
          <label className="admin-form__field">
            <span>Kode</span>
            <input
              type="text"
              value={form.code}
              onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })}
              placeholder="mis. ADMIN"
            />
          </label>
          <label className="admin-form__field admin-form__field--full">
            <span>Deskripsi</span>
            <input
              type="text"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder="Deskripsi role"
            />
          </label>
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

      <Modal
        open={permOpen}
        onOpenChange={setPermOpen}
        title={`Permission — ${permRole?.name ?? ''}`}
        className="admin-modal__content--wide"
        footer={
          <>
            <Button variant="outline" size="sm" onClick={() => setPermOpen(false)}>
              Batal
            </Button>
            <Button size="sm" onClick={() => void savePermissions()} disabled={savingPerms}>
              {savingPerms ? 'Menyimpan...' : 'Simpan'}
            </Button>
          </>
        }
      >
        <div className="admin-perm-groups">
          {[...byResource.entries()].map(([resource, perms]) => (
            <div key={resource} className="admin-perm-card">
              <div className="admin-perm-card__head">
                <strong>{resource}</strong>
                <Tag tone="slate">{resource}.*</Tag>
              </div>
              <div className="admin-perm-card__list">
                {perms.map((p) => {
                  const active = selectedPerms.includes(p.id);
                  return (
                    <label key={p.id} className="admin-perm-item">
                      <input type="checkbox" checked={active} onChange={() => togglePerm(p.id)} />
                      <span>{p.name}</span>
                    </label>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </Modal>
    </section>
  );
}
