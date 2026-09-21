import type { Metadata } from 'next';

import { SettingsManager } from '@/components/admin/settings-manager';

export const metadata: Metadata = {
  title: 'Pengaturan',
};

export default function AdminSettingsPage() {
  return <SettingsManager />;
}
