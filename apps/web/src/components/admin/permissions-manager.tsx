'use client';

import { Pencil, Plus, Save, Trash2 } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';

import { Button } from '@/components/ui/button';
import { LoadingSpinner } from '@/components/ui/loading-spinner';
import { Modal } from '@/components/ui/modal';
import { Select } from '@/components/ui/select';
import { Tag } from '@/components/ui/tag';
import { adminApi, type PermissionItem, type RoleItem } from '@/lib/admin-api';

export function PermissionsManager() {
  const [roles, setRoles] = useState<RoleItem[]>([]);
  const [permissions, setPermissions] = useState<PermissionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [selectedRoleId, setSelectedRoleId] = useState('');
  const [selectedPerms, setSelectedPerms] = useState<number[]>([]);
  const [savingPerms, setSavingPerms] = useState(false);
  const [savedNote, setSavedNote] = useState('');

  // CRUD permission
  const [crudOpen, setCrudOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState({ name: '', resource: '', description: '' });
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      const [roleList, permList] = await Promise.all([
        adminApi.list<RoleItem>('roles'),
        adminApi.list<PermissionItem>('permissions'),
      ]);
      setRoles(roleList);
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

  const loadRoleAccess = useCallback(
    async (roleId: string) => {
      if (!roleId) {
        setSelectedPerms([]);
        return;
      }
      try {
        const res = await fetch(`/api/admin/roles/${roleId}/access`, { cache: 'no-store' });
        const body = (await res.json()) as { data?: { permissionIds: number[] } };
        setSelectedPerms(body.data?.permissionIds ?? []);
      } catch {
        setSelectedPerms([]);
      }
    },
    [],
  );

  useEffect(() => {
    void loadRoleAccess(selectedRoleId);
  }, [selectedRoleId, loadRoleAccess]);

  const byResource = useMemo(() => {
    const map = new Map<string, PermissionItem[]>();
    for (const p of permissions) {
      const arr = map.get(p.resource) ?? [];
      arr.push(p);
      map.set(p.resource, arr);
    }
    return map;
  }, [permissions]);

  const roleOptions = roles.map((r) => ({ value: String(r.id), label: `${r.name} (${r.code})` }));

  const togglePerm = (id: number) => {
    setSelectedPerms((cur) => (cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id]));
  };

  const toggleResource = (perms: PermissionItem[], checked: boolean) => {
    const ids = perms.map((p) => p.id);
    setSelectedPerms((cur) =>
      checked ? [...new Set([...cur, ...ids])] : cur.filter((x) => !ids.includes(x)),
    );
  };

  const savePermissions = async () => {
    if (!selectedRoleId) return;
    setSavingPerms(true);
    setError('');
    try {
      await fetch(`/api/admin/roles/${selectedRoleId}/permissions`, {
        method: 'PUT',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ permissionIds: selectedPerms }),
      });
      setSavedNote('Permission berhasil disimpan.');
      setTimeout(() => setSavedNote(''), 2500);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSavingPerms(false);
    }
  };

  const openCreate = () => {
    setEditingId(null);
    setForm({ name: '', resource: '', description: '' });
    setCrudOpen(true);
  };

  const openEdit = (p: PermissionItem) => {
    setEditingId(p.id);
    setForm({ name: p.name, resource: p.resource, description: p.description ?? '' });
    setCrudOpen(true);
  };

  const handleSave = async () => {
    setSaving(true);
    setError('');
    try {
      const payload = {
        name: form.name,
        resource: form.resource,
        description: form.description || null,
      };
      if (editingId === null) {
        await adminApi.create('permissions', payload);
      } else {
        await adminApi.update('permissions', editingId, payload);
      }
      setCrudOpen(false);
      await load();
      await loadRoleAccess(selectedRoleId);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (p: PermissionItem) => {
    if (!window.confirm(`Hapus permission ${p.name}?`)) return;
    try {
      await adminApi.remove('permissions', p.id);
      await load();
      await loadRoleAccess(selectedRoleId);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  if (loading) return <LoadingSpinner label="Memuat data..." />;

  return (
    <section className="admin-panel">
      <div className="admin-panel__toolbar">
        <h1>Permissions</h1>
        <div className="admin-panel__toolbar-actions">
          <Button variant="outline" size="sm" onClick={openCreate}>
            <Plus size={16} /> Tambah Permission
          </Button>
        </div>
      </div>
      {error ? <p className="text-red-500 text-sm font-semibold">{error}</p> : null}

      <div className="admin-perm-toolbar">
        <div className="admin-form__field" style={{ minWidth: '16rem' }}>
          <span>Pilih Role</span>
          <Select
            value={selectedRoleId}
            onValueChange={setSelectedRoleId}
            options={roleOptions}
            placeholder="Pilih role untuk diatur permissionnya"
          />
        </div>
        {selectedRoleId ? (
          <Button size="sm" onClick={() => void savePermissions()} disabled={savingPerms}>
            <Save size={16} /> {savingPerms ? 'Menyimpan...' : 'Simpan Permission'}
          </Button>
        ) : null}
        {savedNote ? <span className="admin-perm-saved">{savedNote}</span> : null}
      </div>

      {!selectedRoleId ? (
        <p className="muted-text">
          Pilih role terlebih dahulu untuk mengatur permission yang dimilikinya.
        </p>
      ) : (
        <div className="admin-perm-groups">
          {[...byResource.entries()].map(([resource, perms]) => {
            const allChecked = perms.every((p) => selectedPerms.includes(p.id));
            return (
              <div key={resource} className="admin-perm-card">
                <div className="admin-perm-card__head">
                  <label className="admin-perm-item" style={{ padding: 0 }}>
                    <input
                      type="checkbox"
                      checked={allChecked}
                      onChange={(e) => toggleResource(perms, e.target.checked)}
                    />
                    <strong>{resource}</strong>
                  </label>
                  <Tag tone="slate">{resource}.*</Tag>
                </div>
                <div className="admin-perm-card__list">
                  {perms.map((p) => {
                    const active = selectedPerms.includes(p.id);
                    return (
                      <div key={p.id} className="admin-perm-item">
                        <label className="admin-perm-item--grow">
                          <input
                            type="checkbox"
                            checked={active}
                            onChange={() => togglePerm(p.id)}
                          />
                          <span>{p.name}</span>
                        </label>
                        <button
                          type="button"
                          className="admin-icon-btn"
                          onClick={() => openEdit(p)}
                          aria-label="Edit"
                        >
                          <Pencil size={13} />
                        </button>
                        <button
                          type="button"
                          className="admin-icon-btn admin-icon-btn--danger"
                          onClick={() => void handleDelete(p)}
                          aria-label="Hapus"
                        >
                          <Trash2 size={13} />
                        </button>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      )}

      <Modal
        open={crudOpen}
        onOpenChange={setCrudOpen}
        title={editingId === null ? 'Tambah Permission' : 'Edit Permission'}
        footer={
          <>
            <Button variant="outline" size="sm" onClick={() => setCrudOpen(false)}>
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
            <span>Nama (resource.action)</span>
            <input
              type="text"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="mis. users.read"
            />
          </label>
          <label className="admin-form__field">
            <span>Resource</span>
            <input
              type="text"
              value={form.resource}
              onChange={(e) => setForm({ ...form, resource: e.target.value })}
              placeholder="mis. users"
            />
          </label>
          <label className="admin-form__field admin-form__field--full">
            <span>Deskripsi</span>
            <input
              type="text"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder="Deskripsi permission"
            />
          </label>
        </div>
      </Modal>
    </section>
  );
}
