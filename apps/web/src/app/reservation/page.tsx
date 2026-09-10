import type { Metadata } from 'next';

import { AuthGuard } from '@/components/auth/auth-guard';
import { ReservationForm } from '@/components/reservation/reservation-form';
import { Section } from '@/components/ui/section';

export const metadata: Metadata = {
  title: 'Reservasi',
  description:
    'Form reservasi TIEN SALON dengan pilihan multi-layanan dan penyimpanan ke API backend.',
};

export default function ReservationPage() {
  return (
    <AuthGuard>
      <Section
        eyebrow="Reservasi"
        title="Atur jadwal perawatanmu"
        description="Data reservasi disimpan ke API backend dengan autentikasi cookie session."
      >
        <ReservationForm />
      </Section>
    </AuthGuard>
  );
}
