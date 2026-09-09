import type { Metadata } from 'next';

import { PaymentPageContent } from '@/components/payment/payment-page-content';
import { GuardRedirect } from '@/components/reservation/guard-redirect';
import { Section } from '@/components/ui/section';

export const metadata: Metadata = {
  title: 'Simulasi Pembayaran',
  description: 'Halaman simulasi pembayaran TIEN SALON tanpa transaksi nyata.',
};

export default function PaymentPage() {
  return (
    <GuardRedirect requireReservation>
      <Section eyebrow="Payment demo" title="Simulasi Pembayaran">
        <PaymentPageContent />
      </Section>
    </GuardRedirect>
  );
}
