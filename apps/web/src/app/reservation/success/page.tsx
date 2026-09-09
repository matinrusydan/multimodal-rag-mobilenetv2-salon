import type { Metadata } from 'next';

import { GuardRedirect } from '@/components/reservation/guard-redirect';
import { SuccessPage } from '@/components/reservation/success-page';
import { Section } from '@/components/ui/section';

export const metadata: Metadata = {
  title: 'Reservasi Berhasil',
  description: 'Konfirmasi sukses reservasi statis TIEN SALON.',
};

export default function ReservationSuccessPage() {
  return (
    <GuardRedirect requirePayment>
      <Section>
        <SuccessPage />
      </Section>
    </GuardRedirect>
  );
}
