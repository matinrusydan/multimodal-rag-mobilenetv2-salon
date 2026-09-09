'use client';

import Image from 'next/image';

import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

export type PaymentMethodId = 'qris' | 'virtual_account' | 'ewallet' | 'bank_transfer';

export const paymentMethods = [
  {
    id: 'qris',
    label: 'QRIS',
    description: 'Scan QR dummy untuk simulasi pembayaran.',
  },
  {
    id: 'virtual_account',
    label: 'Virtual Account',
    description: 'BCA VA: 1234567890123.',
  },
  {
    id: 'ewallet',
    label: 'E-Wallet',
    description: 'GoPay, OVO, Dana: 081234567890.',
  },
  {
    id: 'bank_transfer',
    label: 'Transfer Bank',
    description: 'BCA 123-456-7890 a.n. TIEN SALON.',
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
