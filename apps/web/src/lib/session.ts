import { SESSION_KEYS } from '@/lib/constants';
import type { PaymentMethod } from '@rag-salon/shared-types';

export interface TienReservationItem {
  serviceId: number;
  serviceName: string;
  price: number;
}

export interface TienReservation {
  id: string;
  userId: number;
  customerName: string;
  email: string;
  phone: string;
  items: TienReservationItem[];
  total: number;
  status: string;
  date: string;
  time: string;
  notes?: string;
  createdAt?: string;
}

export interface TienPayment {
  id?: string;
  method: PaymentMethod;
  methodLabel: string;
  status: string;
  amount: number;
  paidAt?: string;
}

type SessionValue = TienReservation | TienPayment;

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

export function clearReservationFlow() {
  removeSession(SESSION_KEYS.reservation);
  removeSession(SESSION_KEYS.payment);
}
