'use client';

import { useCallback, useEffect, useState } from 'react';

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

  const load = useCallback(async () => {
    try {
      setRows(await adminApi.list<ReservationItem>('reservations'));
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
      <div className="admin-table">
        <table>
          <thead>
            <tr>
              <th>Kode</th>
              <th>Layanan</th>
              <th>Tanggal</th>
              <th>Jam</th>
              <th>Total</th>
              <th>Status</th>
              <th>Ubah Status</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td>
                  <code>{r.id}</code>
                </td>
                <td>{r.items.map((i) => i.serviceName).join(', ') || '-'}</td>
                <td>{r.date}</td>
                <td>{r.time}</td>
                <td>{formatRupiah(r.total)}</td>
                <td>
                  <Tag tone={STATUS_TONE[r.status] ?? 'slate'}>{r.status}</Tag>
                </td>
                <td>
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
                </td>
              </tr>
            ))}
            {rows.length === 0 ? (
              <tr>
                <td colSpan={7} className="admin-table__empty">
                  Belum ada reservasi.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </section>
  );
}
