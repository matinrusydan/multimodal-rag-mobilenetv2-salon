'use client';

import { useCallback, useEffect, useState } from 'react';

import { DataTable } from '@/components/ui/data-table';
import { LoadingSpinner } from '@/components/ui/loading-spinner';
import { Tag } from '@/components/ui/tag';
import { formatRupiah } from '@/lib/format';
import { adminApi, type ReservationItem } from '@/lib/admin-api';

const STATUS_OPTIONS = ['pending', 'confirmed', 'completed', 'cancelled'];

const STATUS_TONE: Record<string, 'green' | 'red' | 'blue' | 'slate' | 'cyan'> = {
  pending: 'slate',
  confirmed: 'blue',
  completed: 'green',
  cancelled: 'red',
};

export function ReservationsManager() {
  const [rows, setRows] = useState<ReservationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [total, setTotal] = useState(0);

  const load = useCallback(async () => {
    try {
      const p = await adminApi.listPaged<ReservationItem>('reservations', page, pageSize);
      setRows(p?.items ?? []);
      setTotal(p?.total ?? 0);
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

  const changeStatus = async (code: string, status: string) => {
    setBusy(code);
    setError('');
    try {
      const res = await fetch(`/api/admin/reservations/${code}/status`, {
        method: 'PUT',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ status }),
      });
      if (!res.ok) {
        const b = (await res.json().catch(() => null)) as { detail?: string; title?: string } | null;
        throw new Error(b?.detail ?? b?.title ?? 'Gagal mengubah status.');
      }
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  };

  if (loading) return <LoadingSpinner label="Memuat data..." />;

  return (
    <section className="admin-panel">
      <div className="admin-panel__toolbar">
        <h1>Reservasi</h1>
      </div>
      {error ? <p className="text-red-500 text-sm font-semibold">{error}</p> : null}
      <DataTable<ReservationItem>
        rows={rows}
        rowKey={(r) => r.id}
        loading={loading}
        emptyText="Belum ada reservasi."
        pagination={{
          page,
          pageSize,
          total,
          onPageChange: setPage,
          onPageSizeChange: (s) => {
            setPageSize(s);
            setPage(1);
          },
        }}
        columns={[
          { key: 'id', label: 'Kode', render: (r) => <code>{r.id}</code> },
          {
            key: 'items',
            label: 'Layanan',
            render: (r) => r.items.map((i) => i.serviceName).join(', ') || '-',
          },
          { key: 'date', label: 'Tanggal' },
          { key: 'time', label: 'Jam' },
          { key: 'total', label: 'Total', render: (r) => formatRupiah(r.total) },
          {
            key: 'status',
            label: 'Status',
            render: (r) => <Tag tone={STATUS_TONE[r.status] ?? 'slate'}>{r.status}</Tag>,
          },
        ]}
        renderRowActions={(r) => (
          <select
            value={r.status}
            disabled={busy === r.id}
            onChange={(e) => void changeStatus(r.id, e.target.value)}
            className="admin-inline-select"
          >
            {STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        )}
      />
    </section>
  );
}
