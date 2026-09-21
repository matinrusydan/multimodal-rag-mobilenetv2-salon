'use client';

export interface RoleItem {
  id: number;
  name: string;
  code: string;
  status?: string;
}

export interface UserItem {
  id: number;
  name: string;
  username: string | null;
  email: string;
  type: number;
  status: string;
  validFrom: string | null;
  validTo: string | null;
  roleIds: number[];
  roles: string[];
}

export interface RouteItem {
  id: number;
  path: string;
  name: string;
  title: string | null;
  parentId: number | null;
  status: string;
  roleIds: number[];
}

export interface MenuItem {
  id: number;
  name: string;
  path: string;
  icon: string | null;
  parentId: number | null;
  sortOrder: number;
  status: string;
  roleIds: number[];
}

export interface PermissionItem {
  id: number;
  name: string;
  resource: string;
  description?: string;
}

export interface ServiceItem {
  id: number;
  name: string;
  slug: string;
  price: number;
  durationMin: number;
  description: string;
  category?: string;
  image?: string;
  isActive: boolean;
}

export interface ReservationItem {
  id: string;
  userId: number;
  items: Array<{ serviceId: number; serviceName: string; price: number }>;
  total: number;
  date: string;
  time: string;
  notes?: string;
  status: string;
  createdAt?: string;
}

async function adminRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api/admin/${path}`, {
    cache: 'no-store',
    ...init,
    headers: {
      ...(init?.body ? { 'content-type': 'application/json' } : {}),
      ...(init?.headers ?? {}),
    },
  });
  const body = (await res.json().catch(() => null)) as {
    data?: T;
    detail?: string;
    title?: string;
  } | null;
  if (!res.ok) {
    throw new Error(body?.detail ?? body?.title ?? 'Terjadi kesalahan.');
  }
  return body?.data as T;
}

export const adminApi = {
  list: <T>(resource: string) => adminRequest<T[]>(resource),
  create: <T>(resource: string, data: unknown) =>
    adminRequest<T>(resource, { method: 'POST', body: JSON.stringify(data) }),
  update: <T>(resource: string, id: number, data: unknown) =>
    adminRequest<T>(`${resource}/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  remove: (resource: string, id: number) =>
    adminRequest<{ status: string }>(`${resource}/${id}`, { method: 'DELETE' }),
};
