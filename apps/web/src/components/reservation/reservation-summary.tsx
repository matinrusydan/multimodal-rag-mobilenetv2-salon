'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { Button } from '@/components/ui/button';
import { LoadingSpinner } from '@/components/ui/loading-spinner';
import { SESSION_KEYS } from '@/lib/constants';
import { formatDate, formatRupiah } from '@/lib/format';
import { type TienReservation, readSession } from '@/lib/session';

export function ReservationSummary() {
  const router = useRouter();
  const [reservation, setReservation] = useState<TienReservation | null>(null);

  useEffect(() => {
    setReservation(readSession<TienReservation>(SESSION_KEYS.reservation));
  }, []);

  if (!reservation) {
    return <LoadingSpinner label="Membaca ringkasan reservasi..." />;
  }

  return (
    <section className="summary-card">
      <div className="summary-card__header">
        <p>Nomor Invoice</p>
        <strong>{reservation.id}</strong>
      </div>
      <div className="summary-card__grid">
        <div>
          <h2>Data Pelanggan</h2>
          <p>{reservation.customerName}</p>
          <p>{reservation.email}</p>
          <p>{reservation.phone}</p>
        </div>
        <div>
          <h2>Detail Reservasi</h2>
          <p>
            {formatDate(reservation.date)} pukul {reservation.time}
          </p>
        </div>
      </div>
      <div className="summary-card__services">
        <h2>Detail Layanan</h2>
        <ul>
          {reservation.items.map((item) => (
            <li key={item.serviceId}>
              <span>{item.serviceName}</span>
              <span>{formatRupiah(item.price)}</span>
            </li>
          ))}
        </ul>
      </div>
      {reservation.notes ? (
        <div className="summary-card__notes">
          <h2>Catatan</h2>
          <p>{reservation.notes}</p>
        </div>
      ) : null}
      <div className="summary-card__total">
        <span>Total Pembayaran</span>
        <strong>{formatRupiah(reservation.total)}</strong>
      </div>
      <div className="summary-card__actions">
        <Button variant="outline" onClick={() => router.push('/reservation')}>
          Ubah Reservasi
        </Button>
        <Button onClick={() => router.push('/payment')}>Lanjut Pembayaran</Button>
      </div>
    </section>
  );
}
