const BASE_URL = process.env.BACKEND_URL ?? 'http://127.0.0.1:4000';

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}/api${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    cache: 'no-store',
  });

  const json = (await res.json()) as { ok: boolean; data: T };

  if (!res.ok || !json.ok) {
    throw new Error('Request API gagal');
  }

  return json.data;
}
