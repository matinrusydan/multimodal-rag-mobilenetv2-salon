'use client';

import { Check } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { LoadingSpinner } from '@/components/ui/loading-spinner';
import { SESSION_KEYS } from '@/lib/constants';
import { formatDate, formatRupiah } from '@/lib/format';
import {
  type TienPayment,
  type TienReservation,
  clearReservationFlow,
  readSession,
} from '@/lib/session';

type SuccessState = {
  reservation: TienReservation;
  payment: TienPayment;
};

export function SuccessPage() {
  const router = useRouter();
  const [state, setState] = useState<SuccessState | null>(null);

  useEffect(() => {
    const reservation = readSession<TienReservation>(SESSION_KEYS.reservation);
    const payment = readSession<TienPayment>(SESSION_KEYS.payment);

    if (reservation && payment) {
      setState({ reservation, payment });
      window.setTimeout(() => clearReservationFlow(), 0);
    }
  }, []);

  if (!state) {
    return <LoadingSpinner label="Menyiapkan konfirmasi..." />;
  }

  const { reservation, payment } = state;

  return (
    <section className="success-card">
      <div className="success-card__icon">
        <Check size={34} />
      </div>
      <h1>Reservasi Berhasil! 🎉</h1>
      <p>Tim TIEN SALON akan menghubungi Anda untuk konfirmasi.</p>
      <div className="success-card__badges">
        <Badge tone="amber">Menunggu Konfirmasi</Badge>
        <Badge tone="success">Simulasi Berhasil</Badge>
      </div>
      <div className="summary-card success-card__summary">
        <div className="summary-card__header">
          <p>Nomor Invoice</p>
          <strong>{reservation.id}</strong>
        </div>
        <ul className="success-card__services">
          {reservation.items.map((item) => (
            <li key={item.serviceId}>
              <span>{item.serviceName}</span>
              <span>{formatRupiah(item.price)}</span>
            </li>
          ))}
        </ul>
        <p>
          {formatDate(reservation.date)} pukul {reservation.time}
        </p>
        <p>Metode pembayaran: {payment.methodLabel}</p>
        <p>Status pembayaran: {payment.status}</p>
        <p>Total dibayar: {formatRupiah(payment.amount)}</p>
      </div>
      <div className="summary-card__actions">
        <Button href="/home">Kembali ke Beranda</Button>
        <Button variant="outline" onClick={() => router.push('/reservation')}>
          Buat Reservasi Lagi
        </Button>
      </div>
    </section>
  );
}
