'use client';

import { Pencil, Plus, Trash2 } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';

import { Button } from '@/components/ui/button';
import { LoadingSpinner } from '@/components/ui/loading-spinner';
import { Modal } from '@/components/ui/modal';
import { MultiSelect } from '@/components/ui/multiselect';
import { Select } from '@/components/ui/select';
import { Tag } from '@/components/ui/tag';
import { adminApi, type RoleItem, type UserItem } from '@/lib/admin-api';

interface FormState {
  name: string;
  username: string;
  email: string;
  password: string;
  type: string;
  status: string;
  validFrom: string;
  validTo: string;
  roleIds: string[];
}

const EMPTY: FormState = {
  name: '',
  username: '',
  email: '',
  password: '',
  type: '1',
  status: 'active',
  validFrom: '',
  validTo: '',
  roleIds: [],
};

export function UsersManager() {
  const [rows, setRows] = useState<UserItem[]>([]);
  const [roles, setRoles] = useState<RoleItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [open, setOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<FormState>(EMPTY);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      const [users, roleList] = await Promise.all([
        adminApi.list<UserItem>('users'),
        adminApi.list<RoleItem>('roles'),
      ]);
      setRows(users);
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

  const openCreate = () => {
    setEditingId(null);
    setForm(EMPTY);
    setOpen(true);
  };

  const openEdit = (u: UserItem) => {
    setEditingId(u.id);
    setForm({
      name: u.name,
      username: u.username ?? '',
      email: u.email,
      password: '',
      type: String(u.type),
      status: u.status,
      validFrom: u.validFrom ?? '',
      validTo: u.validTo ?? '',
      roleIds: (u.roleIds ?? []).map(String),
    });
    setOpen(true);
  };

  const handleSave = async () => {
    setSaving(true);
    setError('');
    try {
      const payload: Record<string, unknown> = {
        name: form.name,
        username: form.username || null,
        email: form.email,
        type: Number(form.type),
        status: form.status,
        validFrom: form.validFrom || null,
        validTo: form.validTo || null,
        roleIds: form.roleIds.map(Number),
      };
      if (form.password) payload.password = form.password;
      if (editingId === null && !form.password) {
        setError('Password wajib diisi untuk pengguna baru.');
        setSaving(false);
        return;
      }
      if (editingId === null) {
        await adminApi.create('users', payload);
      } else {
        await adminApi.update('users', editingId, payload);
      }
      setOpen(false);
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('Yakin ingin menghapus pengguna ini?')) return;
    try {
      await adminApi.remove('users', id);
      await load();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  if (loading) return <LoadingSpinner label="Memuat data..." />;

  return (
    <section className="admin-panel">
      <div className="admin-panel__toolbar">
        <h1>Pengguna</h1>
        <div className="admin-panel__toolbar-actions">
          <Button size="sm" onClick={openCreate}>
            <Plus size={16} /> Tambah Pengguna
          </Button>
        </div>
      </div>
      {error ? <p className="text-red-500 text-sm font-semibold">{error}</p> : null}
      <div className="admin-table">
        <table>
          <thead>
            <tr>
              <th>Nama</th>
              <th>Username</th>
              <th>Email</th>
              <th>Roles</th>
              <th>Status</th>
              <th>Berlaku</th>
              <th>Aksi</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((u) => (
              <tr key={u.id}>
                <td>{u.name}</td>
                <td>{u.username ?? '-'}</td>
                <td>{u.email}</td>
                <td>
                  {u.roles?.length ? u.roles.map((r) => <Tag key={r} tone="cyan">{r}</Tag>) : '-'}
                </td>
                <td>
                  <Tag tone={u.status === 'active' ? 'green' : 'red'}>
                    {u.status === 'active' ? 'Aktif' : 'Nonaktif'}
                  </Tag>
                </td>
                <td>
                  {u.validFrom || u.validTo
                    ? `${u.validFrom ?? '…'} → ${u.validTo ?? '…'}`
                    : '-'}
                </td>
                <td>
                  <div className="admin-table__actions">
                    <button
                      type="button"
                      className="admin-icon-btn"
                      onClick={() => openEdit(u)}
                      aria-label="Edit"
                    >
                      <Pencil size={14} />
                    </button>
                    <button
                      type="button"
                      className="admin-icon-btn admin-icon-btn--danger"
                      onClick={() => void handleDelete(u.id)}
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
                <td colSpan={7} className="admin-table__empty">
                  Belum ada pengguna.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      <Modal
        open={open}
        onOpenChange={setOpen}
        title={editingId === null ? 'Tambah Pengguna' : 'Edit Pengguna'}
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
            <span>Username</span>
            <input
              type="text"
              value={form.username}
              onChange={(e) => setForm({ ...form, username: e.target.value })}
              placeholder="mis. budi.santoso"
            />
          </label>
          <label className="admin-form__field">
            <span>Nama Lengkap</span>
            <input
              type="text"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="mis. Budi Santoso"
            />
          </label>
          <label className="admin-form__field">
            <span>Email</span>
            <input
              type="email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              placeholder="nama@email.com"
            />
          </label>
          <label className="admin-form__field">
            <span>Password {editingId !== null ? '(kosongkan bila tidak diubah)' : ''}</span>
            <input
              type="password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              placeholder="min. 8 karakter"
            />
          </label>
          <div className="admin-form__field admin-form__field--full">
            <span>Roles</span>
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
          <div className="admin-form__field">
            <span>Berlaku Dari</span>
            <input
              type="date"
              value={form.validFrom}
              onChange={(e) => setForm({ ...form, validFrom: e.target.value })}
            />
          </div>
          <div className="admin-form__field">
            <span>Berlaku Sampai</span>
            <input
              type="date"
              value={form.validTo}
              onChange={(e) => setForm({ ...form, validTo: e.target.value })}
            />
          </div>
        </div>
      </Modal>
    </section>
  );
}
