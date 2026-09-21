'use client';

import { CreditCard, Scissors, ShoppingBag, TrendingUp } from 'lucide-react';
import Link from 'next/link';
import { useEffect, useState } from 'react';

import { formatRupiah } from '@/lib/format';

interface PaymentSummary {
  totalPaid: number;
  countPaid: number;
  pendingCount: number;
}

interface ReservationStats {
  total: number;
  byStatus: Array<{ status: string; count: number }>;
}

interface ServiceSummary {
  stats: { total: number; active: number };
}

interface Stats {
  revenue: PaymentSummary | null;
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

export function AdminStats() {
  const [stats, setStats] = useState<Stats>({ revenue: null, reservations: null, services: null });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      fetchAdmin<PaymentSummary>('payments/summary'),
      fetchAdmin<ReservationStats>('reservations/stats'),
      fetchAdmin<ServiceSummary>('services/summary'),
    ]).then(([revenue, reservations, services]) => {
      if (!cancelled) {
        setStats({ revenue, reservations, services });
        setLoading(false);
      }
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const cards = [
    {
      icon: TrendingUp,
      label: 'Pemasukan',
      value: stats.revenue ? formatRupiah(stats.revenue.totalPaid) : '—',
      desc: stats.revenue
        ? `${stats.revenue.countPaid} transaksi lunas`
        : 'Tidak tersedia',
    },
    {
      icon: ShoppingBag,
      label: 'Reservasi',
      value: stats.reservations ? String(stats.reservations.total) : '—',
      desc: stats.reservations
        ? stats.reservations.byStatus.map((s) => `${s.count} ${s.status}`).join(', ') || 'belum ada'
        : 'Tidak tersedia',
    },
    {
      icon: Scissors,
      label: 'Layanan',
      value: stats.services ? String(stats.services.stats.active) : '—',
      desc: stats.services ? `${stats.services.stats.total} total layanan` : 'Tidak tersedia',
    },
    {
      icon: CreditCard,
      label: 'Pending Bayar',
      value: stats.revenue ? String(stats.revenue.pendingCount) : '—',
      desc: 'pembayaran belum lunas',
    },
  ];

  return (
    <div className="admin-stats">
      <div className="admin-stats__head">
        <h2>Statistik</h2>
        <Link href="/admin/reports" className="admin-stats__link">
          Lihat laporan lengkap →
        </Link>
      </div>
      <div className="admin-stats__grid">
        {cards.map((card) => {
          const Icon = card.icon;
          return (
            <Link key={card.label} href="/admin/reports" className="admin-stat-card">
              <div className="admin-stat-card__icon">
                <Icon size={20} />
              </div>
              <div>
                <span className="admin-stat-card__label">{card.label}</span>
                <strong className="admin-stat-card__value">
                  {loading ? '…' : card.value}
                </strong>
                <span className="admin-stat-card__desc">{card.desc}</span>
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
