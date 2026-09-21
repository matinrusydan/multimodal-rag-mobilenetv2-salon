import type { Metadata } from 'next';

import { ReservationsManager } from '@/components/admin/reservations-manager';

export const metadata: Metadata = {
  title: 'Kelola Reservasi',
};

export default function AdminReservationsPage() {
  return <ReservationsManager />;
}
