'use client';

import { useCallback, useEffect, useState } from 'react';

export const AUTH_CHANGE_EVENT = 'tien-auth-change';

export interface AuthUser {
  id: number;
  name: string;
  email: string;
  type: number;
  permissions: string[];
  roles: string[];
}

export function notifyAuthChange() {
  window.dispatchEvent(new Event(AUTH_CHANGE_EVENT));
}

export function useAuth() {
  const [auth, setAuth] = useState<{ user: AuthUser } | null>(null);
  const [isReady, setIsReady] = useState(false);

  const load = useCallback(async () => {
    try {
      const res = await fetch('/api/auth/session', { cache: 'no-store' });
      if (res.ok) {
        const body = (await res.json()) as { data: { user: AuthUser } };
        setAuth({ user: body.data.user });
      } else {
        setAuth(null);
      }
    } catch {
      setAuth(null);
    } finally {
      setIsReady(true);
    }
  }, []);

  useEffect(() => {
    load();
    window.addEventListener(AUTH_CHANGE_EVENT, load);
    return () => {
      window.removeEventListener(AUTH_CHANGE_EVENT, load);
    };
  }, [load]);

  const logout = useCallback(async () => {
    try {
      await fetch('/api/auth/logout', { method: 'POST' });
    } finally {
      setAuth(null);
      setIsReady(true);
      notifyAuthChange();
    }
  }, []);

  return {
    auth,
    user: auth?.user ?? null,
    isLoggedIn: Boolean(auth),
    isReady,
    logout,
    refresh: load,
  };
}
