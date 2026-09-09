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
import { type TienReservation, readSession, writeSession } from '@/lib/session';

export function PaymentPageContent() {
  const router = useRouter();
  const [reservation, setReservation] = useState<TienReservation | null>(null);
  const [method, setMethod] = useState<PaymentMethodId>('qris');
  const [ewalletMethod, setEwalletMethod] = useState('GoPay');

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

  const handleSuccess = () => {
    writeSession(SESSION_KEYS.payment, {
      method,
      methodLabel: method === 'ewallet' ? `E-Wallet - ${ewalletMethod}` : selectedMethod.label,
    });
    router.push('/reservation/success');
  };

  return (
    <section className="payment-page">
      <div className="payment-page__banner">
        <Badge tone="amber">SIMULASI PEMBAYARAN — Tidak ada transaksi nyata</Badge>
      </div>
      <div className="payment-page__summary">
        <span>Invoice</span>
        <strong>{reservation.invoiceNumber}</strong>
        <span>Total Pembayaran</span>
        <strong>{formatRupiah(reservation.servicePrice)}</strong>
      </div>
      <PaymentMethod selected={method} onSelect={setMethod} />
      {method === 'ewallet' ? (
        <div className="payment-submethods" aria-label="Pilihan sub-metode e-wallet">
          {['GoPay', 'OVO', 'Dana'].map((item) => (
            <button
              key={item}
              type="button"
              className={
                ewalletMethod === item
                  ? 'payment-submethods__item payment-submethods__item--active'
                  : 'payment-submethods__item'
              }
              onClick={() => setEwalletMethod(item)}
            >
              {item}
            </button>
          ))}
          <p>Nomor dummy: 081234567890</p>
        </div>
      ) : null}
      <PaymentInstructions method={method} />
      <div className="payment-page__timer" aria-label="Countdown simulasi 60 detik">
        00:60
      </div>
      <Button size="lg" onClick={handleSuccess}>
        Simulasikan Pembayaran Berhasil
      </Button>
    </section>
  );
}
