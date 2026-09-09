import type { Metadata } from 'next';

import { GuardRedirect } from '@/components/reservation/guard-redirect';
import { ReservationSummary } from '@/components/reservation/reservation-summary';
import { Section } from '@/components/ui/section';

export const metadata: Metadata = {
  title: 'Ringkasan Reservasi',
  description: 'Ringkasan reservasi statis TIEN SALON dari sessionStorage.',
};

export default function ReservationSummaryPage() {
  return (
    <GuardRedirect requireReservation>
      <Section eyebrow="Ringkasan" title="Ringkasan Reservasi">
        <ReservationSummary />
      </Section>
    </GuardRedirect>
  );
}
