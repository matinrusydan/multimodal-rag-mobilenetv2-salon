'use client';

import { useRouter } from 'next/navigation';
import type React from 'react';
import { useEffect, useState } from 'react';

import { LoadingSpinner } from '@/components/ui/loading-spinner';
import { SESSION_KEYS } from '@/lib/constants';
import { type TienPayment, type TienReservation, readSession } from '@/lib/session';
import { useAuth } from '@/lib/use-auth';

type GuardRedirectProps = {
  children: React.ReactNode;
  requireReservation?: boolean;
  requirePayment?: boolean;
  reservationRedirect?: string;
  missingFlowRedirect?: string;
};

export function GuardRedirect({
  children,
  requireReservation = false,
  requirePayment = false,
  reservationRedirect = '/reservation',
  missingFlowRedirect = '/home',
}: GuardRedirectProps) {
  const router = useRouter();
  const { isLoggedIn, isReady } = useAuth();
  const [canRender, setCanRender] = useState(false);

  useEffect(() => {
    if (!isReady) {
      return;
    }

    if (!isLoggedIn) {
      router.replace('/login');
      return;
    }

    const reservation = readSession<TienReservation>(SESSION_KEYS.reservation);
    const payment = readSession<TienPayment>(SESSION_KEYS.payment);

    if (requireReservation && !reservation) {
      router.replace(reservationRedirect);
      return;
    }

    if (requirePayment && (!reservation || !payment)) {
      router.replace(missingFlowRedirect);
      return;
    }

    setCanRender(true);
  }, [
    isLoggedIn,
    isReady,
    missingFlowRedirect,
    requirePayment,
    requireReservation,
    reservationRedirect,
    router,
  ]);

  if (!canRender) {
    return <LoadingSpinner label="Menyiapkan halaman..." />;
  }

  return <>{children}</>;
}
