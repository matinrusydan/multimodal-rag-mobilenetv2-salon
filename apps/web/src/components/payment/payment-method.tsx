'use client';

import Image from 'next/image';

import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import type { PaymentMethod as PaymentMethodEnum } from '@rag-salon/shared-types';

export type PaymentMethodId = PaymentMethodEnum;

export const paymentMethods = [
  {
    id: 'qris',
    label: 'QRIS',
    description: 'Scan QR dummy untuk simulasi pembayaran.',
  },
  {
    id: 'transfer',
    label: 'Transfer Bank',
    description: 'Transfer ke BCA 123-456-7890 a.n. TIEN SALON.',
  },
  {
    id: 'cash',
    label: 'Tunai di Tempat',
    description: 'Bayar langsung di kasir salon.',
  },
] satisfies { id: PaymentMethodId; label: string; description: string }[];

type PaymentMethodProps = {
  selected: PaymentMethodId;
  onSelect: (method: PaymentMethodId) => void;
};

export function PaymentMethod({ selected, onSelect }: PaymentMethodProps) {
  return (
    <div className="payment-method-grid">
      {paymentMethods.map((method) => (
        <button
          key={method.id}
          type="button"
          className={cn(
            'payment-method-card',
            selected === method.id && 'payment-method-card--active',
          )}
          onClick={() => onSelect(method.id)}
        >
          <span>{method.label}</span>
          <p>{method.description}</p>
          {selected === method.id ? <Badge>Dipilih</Badge> : null}
        </button>
      ))}
      {selected === 'qris' ? (
        <div className="payment-method-card payment-method-card--qr">
          <Image
            src="/images/payment/qr-dummy.png"
            alt="QRIS dummy untuk simulasi pembayaran"
            width={360}
            height={360}
          />
        </div>
      ) : null}
    </div>
  );
}
