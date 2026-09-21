'use client';

import { useEffect, useState } from 'react';

import { formatRupiah } from '@/lib/format';

interface PaymentSummary {
  totalPaid: number;
  countPaid: number;
  pendingCount: number;
  byMethod: Array<{ method: string; total: number; count: number }>;
}

interface ReservationStats {
  total: number;
  byStatus: Array<{ status: string; count: number }>;
  byDay: Array<{ date: string; count: number; total: number }>;
}

interface ServiceSummary {
  stats: { total: number; active: number; minPrice: number; maxPrice: number };
  byCategory: Array<{
    category: string | null;
    count: number;
    minPrice: number;
    maxPrice: number;
    avgDurationMin: number;
  }>;
}

interface Reports {
  payments: PaymentSummary | null;
  reservations: ReservationStats | null;
  services: ServiceSummary | null;
}

async function fetchAdmin<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`/api/admin/${path}`, { cache: 'no-store' });
    if (!res.ok) return null;
    const body = (await res.json()) as { data?: T };
    return body.data ?? null;
  } catch {
    return null;
  }
}

export default function AdminReportsPage() {
  const [data, setData] = useState<Reports>({
    payments: null,
    reservations: null,
    services: null,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      fetchAdmin<PaymentSummary>('payments/summary'),
      fetchAdmin<ReservationStats>('reservations/stats'),
      fetchAdmin<ServiceSummary>('services/summary'),
    ]).then(([payments, reservations, services]) => {
      if (!cancelled) {
        setData({ payments, reservations, services });
        setLoading(false);
      }
    });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section className="admin-panel">
      <h1>Laporan</h1>
      <p className="muted-text">
        Ringkasan pemasukan, reservasi, dan layanan (data langsung dari database).
      </p>

      {loading ? <p className="muted-text">Memuat laporan…</p> : null}

      {!loading ? (
        <>
          <div className="admin-report-block">
            <h2>Pemasukan</h2>
            {data.payments ? (
              <>
                <div className="admin-report-kpis">
                  <div>
                    <strong>{formatRupiah(data.payments.totalPaid)}</strong>
                    <span>Total lunas</span>
                  </div>
                  <div>
                    <strong>{data.payments.countPaid}</strong>
                    <span>Transaksi lunas</span>
                  </div>
                  <div>
                    <strong>{data.payments.pendingCount}</strong>
                    <span>Pending</span>
                  </div>
                </div>
                <table className="admin-report-table">
                  <thead>
                    <tr>
                      <th>Metode</th>
                      <th>Jumlah</th>
                      <th>Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.payments.byMethod.length === 0 ? (
                      <tr>
                        <td colSpan={3} className="admin-table__empty">
                          Belum ada pembayaran.
                        </td>
                      </tr>
                    ) : (
                      data.payments.byMethod.map((m) => (
                        <tr key={m.method}>
                          <td>{m.method}</td>
                          <td>{m.count}</td>
                          <td>{formatRupiah(m.total)}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </>
            ) : (
              <p className="muted-text">Data pemasukan tidak tersedia.</p>
            )}
          </div>

          <div className="admin-report-block">
            <h2>Reservasi</h2>
            {data.reservations ? (
              <>
                <div className="admin-report-kpis">
                  <div>
                    <strong>{data.reservations.total}</strong>
                    <span>Total reservasi</span>
                  </div>
                  {data.reservations.byStatus.map((s) => (
                    <div key={s.status}>
                      <strong>{s.count}</strong>
                      <span>{s.status}</span>
                    </div>
                  ))}
                </div>
                <table className="admin-report-table">
                  <thead>
                    <tr>
                      <th>Tanggal</th>
                      <th>Jumlah</th>
                      <th>Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.reservations.byDay.length === 0 ? (
                      <tr>
                        <td colSpan={3} className="admin-table__empty">
                          Belum ada reservasi 7 hari terakhir.
                        </td>
                      </tr>
                    ) : (
                      data.reservations.byDay.map((d) => (
                        <tr key={d.date}>
                          <td>{d.date}</td>
                          <td>{d.count}</td>
                          <td>{formatRupiah(d.total)}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </>
            ) : (
              <p className="muted-text">Data reservasi tidak tersedia.</p>
            )}
          </div>

          <div className="admin-report-block">
            <h2>Layanan</h2>
            {data.services ? (
              <>
                <div className="admin-report-kpis">
                  <div>
                    <strong>{data.services.stats.active}</strong>
                    <span>Layanan aktif</span>
                  </div>
                  <div>
                    <strong>{data.services.stats.total}</strong>
                    <span>Total layanan</span>
                  </div>
                  <div>
                    <strong>
                      {formatRupiah(data.services.stats.minPrice)} –{' '}
                      {formatRupiah(data.services.stats.maxPrice)}
                    </strong>
                    <span>Rentang harga</span>
                  </div>
                </div>
                <table className="admin-report-table">
                  <thead>
                    <tr>
                      <th>Kategori</th>
                      <th>Jumlah</th>
                      <th>Harga min</th>
                      <th>Harga max</th>
                      <th>Rata durasi</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.services.byCategory.map((c) => (
                      <tr key={c.category ?? 'umum'}>
                        <td>{c.category ?? 'Umum'}</td>
                        <td>{c.count}</td>
                        <td>{formatRupiah(c.minPrice)}</td>
                        <td>{formatRupiah(c.maxPrice)}</td>
                        <td>{c.avgDurationMin} mnt</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </>
            ) : (
              <p className="muted-text">Data layanan tidak tersedia.</p>
            )}
          </div>
        </>
      ) : null}
    </section>
  );
}
