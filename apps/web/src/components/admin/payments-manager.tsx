'use client';

import { useCallback, useEffect, useState } from 'react';

import { DataTable } from '@/components/ui/data-table';
import { LoadingSpinner } from '@/components/ui/loading-spinner';
import { Tag } from '@/components/ui/tag';
import { formatRupiah } from '@/lib/format';
import type { PaymentItem } from '@/lib/admin-api';

const STATUS_TONE: Record<string, 'green' | 'red' | 'blue' | 'slate' | 'cyan'> = {
  paid: 'green',
  pending: 'slate',
  failed: 'red',
  cancelled: 'red',
};

interface PaymentSummary {
  totalPaid: number;
  countPaid: number;
  pendingCount: number;
}

export function PaymentsManager() {
  const [rows, setRows] = useState<PaymentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [total, setTotal] = useState(0);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [search, setSearch] = useState<string>('');
  const [summary, setSummary] = useState<PaymentSummary | null>(null);

  const loadSummary = useCallback(async () => {
    try {
      const res = await fetch('/api/admin/payments/summary', { cache: 'no-store' });
      if (!res.ok) return;
      const b = (await res.json()) as { data?: PaymentSummary };
      if (b?.data) setSummary(b.data);
    } catch {
      /* ignore */
    }
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: String(page),
        pageSize: String(pageSize),
        limit: String(pageSize),
      });
      if (statusFilter && statusFilter !== 'all') {
        params.set('status', statusFilter);
      }
      if (search.trim()) {
        params.set('search', search.trim());
      }

      const res = await fetch(`/api/admin/payments?${params.toString()}`, { cache: 'no-store' });
      if (!res.ok) {
        const b = (await res.json().catch(() => null)) as { detail?: string; title?: string } | null;
        throw new Error(b?.detail ?? b?.title ?? 'Gagal memuat data pembayaran.');
      }
      const b = (await res.json()) as {
        data?: {
          items?: PaymentItem[];
          total?: number;
        };
      };
      setRows(b?.data?.items ?? []);
      setTotal(b?.data?.total ?? 0);
      setError('');
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, statusFilter, search]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    void loadSummary();
  }, [loadSummary]);

  return (
    <section className="admin-panel">
      <div className="admin-panel__toolbar">
        <h1>Kelola Pembayaran</h1>
      </div>

      {summary ? (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
          <div className="p-4 rounded-xl border border-rose-100 bg-rose-50/40">
            <p className="text-xs font-semibold text-rose-700 uppercase tracking-wider mb-1">Total Lunas</p>
            <p className="text-xl font-bold text-gray-900">{formatRupiah(summary.totalPaid)}</p>
            <p className="text-xs text-gray-500 mt-1">{summary.countPaid} transaksi berhasil</p>
          </div>
          <div className="p-4 rounded-xl border border-amber-100 bg-amber-50/40">
            <p className="text-xs font-semibold text-amber-700 uppercase tracking-wider mb-1">Menunggu Bayar</p>
            <p className="text-xl font-bold text-gray-900">{summary.pendingCount}</p>
            <p className="text-xs text-gray-500 mt-1">transaksi pending</p>
          </div>
          <div className="p-4 rounded-xl border border-gray-100 bg-gray-50">
            <p className="text-xs font-semibold text-gray-600 uppercase tracking-wider mb-1">Total Transaksi</p>
            <p className="text-xl font-bold text-gray-900">{summary.countPaid + summary.pendingCount}</p>
            <p className="text-xs text-gray-500 mt-1">keseluruhan rekaman</p>
          </div>
        </div>
      ) : null}

      <div className="flex flex-wrap items-center gap-3 mb-4">
        <input
          type="text"
          placeholder="Cari kode / pelanggan / reservasi..."
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
          className="admin-input max-w-xs"
        />

        <select
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value);
            setPage(1);
          }}
          className="admin-inline-select"
        >
          <option value="all">Semua Status</option>
          <option value="paid">Lunas (Paid)</option>
          <option value="pending">Pending</option>
          <option value="failed">Gagal / Batal</option>
        </select>
      </div>

      {error ? <p className="text-red-500 text-sm font-semibold mb-3">{error}</p> : null}

      {loading && rows.length === 0 ? (
        <LoadingSpinner label="Memuat pembayaran..." />
      ) : (
        <DataTable<PaymentItem>
          rows={rows}
          rowKey={(r) => r.id}
          loading={loading}
          emptyText="Belum ada transaksi pembayaran."
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
            {
              key: 'code',
              label: 'Kode Pembayaran',
              render: (r) => <code className="font-semibold">{r.code}</code>,
            },
            {
              key: 'reservationCode',
              label: 'Kode Reservasi',
              render: (r) => <code>{r.reservationCode || '-'}</code>,
            },
            {
              key: 'serviceNames',
              label: 'Layanan',
              render: (r) => <span className="text-sm text-gray-700">{r.serviceNames || '-'}</span>,
            },
            {
              key: 'customer',
              label: 'Pelanggan',
              render: (r) => (
                <div>
                  <div className="font-medium text-gray-900">{r.customerName || '-'}</div>
                  {r.customerEmail ? <div className="text-xs text-gray-500">{r.customerEmail}</div> : null}
                </div>
              ),
            },
            {
              key: 'method',
              label: 'Metode',
              render: (r) => <span className="uppercase text-xs font-semibold">{r.method || '-'}</span>,
            },
            {
              key: 'amount',
              label: 'Nominal',
              render: (r) => <span className="font-semibold">{formatRupiah(r.amount)}</span>,
            },
            {
              key: 'status',
              label: 'Status',
              render: (r) => <Tag tone={STATUS_TONE[r.status] ?? 'slate'}>{r.status}</Tag>,
            },
            {
              key: 'paidAt',
              label: 'Waktu Lunas',
              render: (r) => (
                <span className="text-xs text-gray-600">
                  {r.paidAt ? new Date(r.paidAt).toLocaleString('id-ID') : '-'}
                </span>
              ),
            },
          ]}
        />
      )}
    </section>
  );
}
