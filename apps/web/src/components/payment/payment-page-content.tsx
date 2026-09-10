'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';

import { PaymentInstructions } from '@/components/payment/payment-instructions';
import {
  PaymentMethod,
  type PaymentMethodId,
  paymentMethods,
} from '@/components/payment/payment-method';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { LoadingSpinner } from '@/components/ui/loading-spinner';
import { SESSION_KEYS } from '@/lib/constants';
import { formatRupiah } from '@/lib/format';
import { type TienPayment, type TienReservation, readSession, writeSession } from '@/lib/session';

type SimulateResult = {
  paymentId: string;
  status: 'paid';
  amount: number;
  paidAt: string;
};

export function PaymentPageContent() {
  const router = useRouter();
  const [reservation, setReservation] = useState<TienReservation | null>(null);
  const [method, setMethod] = useState<PaymentMethodId>('qris');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    setReservation(readSession<TienReservation>(SESSION_KEYS.reservation));
  }, []);

  const selectedMethod = useMemo(
    () => paymentMethods.find((item) => item.id === method) ?? paymentMethods[0],
    [method],
  );

  if (!reservation) {
    return <LoadingSpinner label="Membaca invoice..." />;
  }

  const handleSuccess = async () => {
    setError('');
    setIsSubmitting(true);
    try {
      const res = await fetch('/api/payments/simulate', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ reservationId: reservation.id, method }),
      });
      const body = (await res.json().catch(() => null)) as {
        data?: SimulateResult;
        detail?: string;
        title?: string;
      } | null;

      if (!res.ok || !body?.data) {
        setError(body?.detail ?? body?.title ?? 'Gagal memproses pembayaran.');
        return;
      }

      const payment = body.data;
      writeSession(SESSION_KEYS.payment, {
        id: payment.paymentId,
        method,
        methodLabel: selectedMethod.label,
        status: payment.status,
        amount: payment.amount,
        paidAt: payment.paidAt,
      });
      router.push('/reservation/success');
    } catch {
      setError('Terjadi kesalahan jaringan. Silakan coba lagi.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className="payment-page">
      <div className="payment-page__banner">
        <Badge tone="amber">SIMULASI PEMBAYARAN — Tidak ada transaksi nyata</Badge>
      </div>
      <div className="payment-page__summary">
        <span>Invoice</span>
        <strong>{reservation.id}</strong>
        <span>Total Pembayaran</span>
        <strong>{formatRupiah(reservation.total)}</strong>
      </div>
      <PaymentMethod selected={method} onSelect={setMethod} />
      <PaymentInstructions method={method} />
      <div className="payment-page__timer" aria-label="Countdown simulasi 60 detik">
        00:60
      </div>
      {error ? <p className="text-red-500 text-sm font-semibold">{error}</p> : null}
      <Button size="lg" onClick={handleSuccess} disabled={isSubmitting}>
        {isSubmitting ? 'Memproses...' : 'Simulasikan Pembayaran Berhasil'}
      </Button>
    </section>
  );
}
