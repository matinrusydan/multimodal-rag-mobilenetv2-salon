import type { Metadata } from 'next';
import { Suspense } from 'react';

import { AuthPage } from '@/components/auth/auth-page';
import { LoadingSpinner } from '@/components/ui/loading-spinner';

export const metadata: Metadata = {
  title: 'Masuk atau Daftar',
  description: 'Masuk atau daftar akun untuk memesan perawatan terbaik di TIEN SALON.',
};

export default function AuthRoute() {
  return (
    <Suspense fallback={<LoadingSpinner label="Menyiapkan halaman..." />}>
      <AuthPage />
    </Suspense>
  );
}
