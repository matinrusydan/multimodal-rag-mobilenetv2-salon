'use client';

import { useRouter } from 'next/navigation';
import type React from 'react';
import { useEffect } from 'react';

import { LoadingSpinner } from '@/components/ui/loading-spinner';
import { useAuth } from '@/lib/use-auth';

type AuthGuardProps = {
  children: React.ReactNode;
  redirectTo?: string;
};

export function AuthGuard({ children, redirectTo = '/login' }: AuthGuardProps) {
  const router = useRouter();
  const { isLoggedIn, isReady } = useAuth();

  useEffect(() => {
    if (isReady && !isLoggedIn) {
      router.replace(redirectTo);
    }
  }, [isLoggedIn, isReady, redirectTo, router]);

  if (!isReady || !isLoggedIn) {
    return <LoadingSpinner label="Memeriksa akses..." />;
  }

  return <>{children}</>;
}
