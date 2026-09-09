import type { Metadata } from 'next';

import { AuthGuard } from '@/components/auth/auth-guard';
import { ReservationForm } from '@/components/reservation/reservation-form';
import { Section } from '@/components/ui/section';

export const metadata: Metadata = {
  title: 'Reservasi',
  description: 'Form reservasi statis TIEN SALON dengan validasi client-side dan sessionStorage.',
};

export default function ReservationPage() {
  return (
    <AuthGuard>
      <Section
        eyebrow="Reservasi"
        title="Atur jadwal perawatanmu"
        description="Form ini bersifat statis dan menyimpan data reservasi ke sessionStorage sesuai PRD."
      >
        <ReservationForm />
      </Section>
    </AuthGuard>
  );
}
