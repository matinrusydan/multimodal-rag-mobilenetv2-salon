import type { Metadata } from 'next';

import { PaymentsManager } from '@/components/admin/payments-manager';

export const metadata: Metadata = {
  title: 'Kelola Pembayaran',
};

export default function AdminPaymentsPage() {
  return <PaymentsManager />;
}
