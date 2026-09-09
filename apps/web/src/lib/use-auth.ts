'use client';

import { useEffect, useState } from 'react';

import { SESSION_KEYS } from '@/lib/constants';
import { type TienAuth, clearAuthSession, readSession } from '@/lib/session';

export const AUTH_CHANGE_EVENT = 'tien-auth-change';

export function notifyAuthChange() {
  window.dispatchEvent(new Event(AUTH_CHANGE_EVENT));
}

export function useAuth() {
  const [auth, setAuth] = useState<TienAuth | null>(null);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    const syncAuth = () => {
      setAuth(readSession<TienAuth>(SESSION_KEYS.auth));
      setIsReady(true);
    };

    syncAuth();
    window.addEventListener(AUTH_CHANGE_EVENT, syncAuth);
    window.addEventListener('storage', syncAuth);

    return () => {
      window.removeEventListener(AUTH_CHANGE_EVENT, syncAuth);
      window.removeEventListener('storage', syncAuth);
    };
  }, []);

  const logout = () => {
    clearAuthSession();
    notifyAuthChange();
  };

  return {
    auth,
    isLoggedIn: Boolean(auth?.isLoggedIn),
    isReady,
    logout,
  };
}
