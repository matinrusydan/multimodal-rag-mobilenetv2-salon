import { SESSION_KEYS } from '@/lib/constants';

export interface TienAuth {
  isLoggedIn: boolean;
  user: {
    name: string;
    email: string;
  };
}

export interface TienReservation {
  customerName: string;
  email: string;
  phone: string;
  serviceId: string;
  serviceName: string;
  servicePrice: number;
  serviceDurationMinutes: number;
  date: string;
  time: string;
  notes: string;
  invoiceNumber: string;
}

export interface TienPayment {
  method: 'qris' | 'virtual_account' | 'ewallet' | 'bank_transfer';
  methodLabel: string;
}

type SessionValue = TienAuth | TienReservation | TienPayment;

function canUseSessionStorage() {
  return typeof window !== 'undefined' && typeof window.sessionStorage !== 'undefined';
}

export function readSession<T>(key: string): T | null {
  if (!canUseSessionStorage()) {
    return null;
  }

  const raw = window.sessionStorage.getItem(key);

  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw) as T;
  } catch {
    window.sessionStorage.removeItem(key);
    return null;
  }
}

export function writeSession(key: string, value: SessionValue) {
  if (!canUseSessionStorage()) {
    return;
  }

  window.sessionStorage.setItem(key, JSON.stringify(value));
}

export function removeSession(key: string) {
  if (!canUseSessionStorage()) {
    return;
  }

  window.sessionStorage.removeItem(key);
}

export function clearAuthSession() {
  removeSession(SESSION_KEYS.auth);
}

export function clearReservationFlow() {
  removeSession(SESSION_KEYS.reservation);
  removeSession(SESSION_KEYS.payment);
}
