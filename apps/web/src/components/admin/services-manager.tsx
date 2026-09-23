'use client';

import { Pencil, Plus, Trash2 } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';

import { Button } from '@/components/ui/button';
import { DataTable } from '@/components/ui/data-table';
import { InputNumber } from '@/components/ui/input-number';
import { LoadingSpinner } from '@/components/ui/loading-spinner';
import { Modal } from '@/components/ui/modal';
import { Switch } from '@/components/ui/switch';
import { Tag } from '@/components/ui/tag';
import { formatRupiah } from '@/lib/format';
import { adminApi, type ServiceItem } from '@/lib/admin-api';

interface FormState {
  name: string;
  slug: string;
  category: string;
  price: number;
  durationMin: number;
  description: string;
  image: string;
  isActive: boolean;
}

const EMPTY: FormState = {
  name: '',
  slug: '',
  category: '',
  price: 0,
  durationMin: 60,
  description: '',
  image: '',
  isActive: true,
};

function slugify(text: string): string {
  return text
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

export function ServicesManager() {
  const [rows, setRows] = useState<ServiceItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [open, setOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<FormState>(EMPTY);
  const [saving, setSaving] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [total, setTotal] = useState(0);

  const load = useCallback(async () => {
    try {
      const p = await adminApi.listPaged<ServiceItem>('services/admin/all', page, pageSize);
      setRows(p.items);
      setTotal(p.total);
      setError('');
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [page, pageSize]);

  useEffect(() => {
    void load();
  }, [load]);

  const openCreate = () => {
    setEditingId(null);
    setForm(EMPTY);
    setOpen(true);
  };

  const openEdit = (s: ServiceItem) => {
    setEditingId(s.id);
    setForm({
      name: s.name,
      slug: s.slug,
      category: s.category ?? '',
      price: s.price,
      durationMin: s.durationMin,
      description: s.description ?? '',
      image: s.image ?? '',
      isActive: s.isActive,
    });
    setOpen(true);
  };

  const handleSave = async () => {
    setSaving(true);
    setError('');
    try {
      const payload: Record<string, unknown> = {
        name: form.name,
        slug: form.slug || slugify(form.name),
        category: form.category || null,
        price: form.price,
        durationMin: form.durationMin,
        description: form.description || null,
        image: form.image || null,
        isActive: form.isActive,
      };
      if (editingId === null) {
        await adminApi.create('services', payload);
      } else {
        await fetch(`/api/admin/services/id/${editingId}`, {
          method: 'PUT',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify(payload),
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

  const handleDelete = async (s: ServiceItem) => {
    if (!window.confirm(`Hapus layanan ${s.name}?`)) return;
    try {
      await fetch(`/api/admin/services/id/${s.id}`, { method: 'DELETE' });
      await load();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  if (loading) return <LoadingSpinner label="Memuat data..." />;

  return (
    <section className="admin-panel">
      <div className="admin-panel__toolbar">
        <h1>Layanan &amp; Harga</h1>
        <div className="admin-panel__toolbar-actions">
          <Button size="sm" onClick={openCreate}>
            <Plus size={16} /> Tambah Layanan
          </Button>
        </div>
      </div>
      {error ? <p className="text-red-500 text-sm font-semibold">{error}</p> : null}
      <DataTable<ServiceItem>
        rows={rows}
        rowKey={(s) => s.id}
        loading={loading}
        emptyText="Belum ada layanan."
        pagination={{
          page,
          pageSize,
          total,
          onPageChange: setPage,
          onPageSizeChange: (sz) => {
            setPageSize(sz);
            setPage(1);
          },
        }}
        columns={[
          { key: 'name', label: 'Nama' },
          { key: 'slug', label: 'Slug', render: (s) => <code>{s.slug}</code> },
          { key: 'category', label: 'Kategori', render: (s) => s.category ?? '-' },
          { key: 'price', label: 'Harga', render: (s) => formatRupiah(s.price) },
          { key: 'durationMin', label: 'Durasi', render: (s) => `${s.durationMin} mnt` },
          {
            key: 'isActive',
            label: 'Status',
            render: (s) => (
              <Tag tone={s.isActive ? 'green' : 'red'}>{s.isActive ? 'Aktif' : 'Nonaktif'}</Tag>
            ),
          },
        ]}
        renderRowActions={(s) => (
          <div className="admin-table__actions">
            <button type="button" className="admin-icon-btn" onClick={() => openEdit(s)} aria-label="Edit">
              <Pencil size={14} />
            </button>
            <button
              type="button"
              className="admin-icon-btn admin-icon-btn--danger"
              onClick={() => void handleDelete(s)}
              aria-label="Hapus"
            >
              <Trash2 size={14} />
            </button>
          </div>
        )}
      />

      <Modal
        open={open}
        onOpenChange={setOpen}
        title={editingId === null ? 'Tambah Layanan' : 'Edit Layanan'}
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
            <span>Nama Layanan</span>
            <input
              type="text"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="mis. Signature Hair Spa"
            />
          </label>
          <label className="admin-form__field">
            <span>Slug (opsional)</span>
            <input
              type="text"
              value={form.slug}
              onChange={(e) => setForm({ ...form, slug: e.target.value })}
              placeholder="otomatis dari nama"
            />
          </label>
          <label className="admin-form__field">
            <span>Kategori</span>
            <input
              type="text"
              value={form.category}
              onChange={(e) => setForm({ ...form, category: e.target.value })}
              placeholder="mis. Hair Treatment"
            />
          </label>
          <div className="admin-form__field">
            <span>Harga (Rp)</span>
            <InputNumber
              value={form.price}
              onChange={(v) => setForm({ ...form, price: v })}
              min={0}
              max={100000000}
            />
          </div>
          <div className="admin-form__field">
            <span>Durasi (menit)</span>
            <InputNumber
              value={form.durationMin}
              onChange={(v) => setForm({ ...form, durationMin: v })}
              min={1}
              max={600}
            />
          </div>
          <div className="admin-form__field">
            <span>Status</span>
            <Switch
              checked={form.isActive}
              onCheckedChange={(c) => setForm({ ...form, isActive: c })}
              onLabel="Aktif"
              offLabel="Nonaktif"
            />
          </div>
          <label className="admin-form__field admin-form__field--full">
            <span>Deskripsi</span>
            <textarea
              rows={3}
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder="Deskripsi layanan"
            />
          </label>
          <label className="admin-form__field admin-form__field--full">
            <span>Gambar (path/URL)</span>
            <input
              type="text"
              value={form.image}
              onChange={(e) => setForm({ ...form, image: e.target.value })}
              placeholder="mis. /images/services/creambath.png"
            />
          </label>
        </div>
      </Modal>
    </section>
  );
}
