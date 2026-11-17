import type { NextRequest } from 'next/server';

import { ApiError, problem, routeError, routeOk } from '@/lib/backend';

const BACKEND_URL = process.env.BACKEND_URL ?? 'http://127.0.0.1:4000';

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const image = formData.get('image');
    if (!(image instanceof File)) {
      return routeError(problem(400, 'Permintaan tidak valid', 'Gambar wajib diunggah.'));
    }

    const forward = new FormData();
    forward.append('image', image);

    const res = await fetch(`${BACKEND_URL}/api/analyze`, {
      method: 'POST',
      body: forward,
      cache: 'no-store',
    });
    const body = (await res.json().catch(() => null)) as {
      data?: unknown;
      title?: string;
      detail?: string;
    } | null;
    if (!res.ok) {
      throw new ApiError(res.status, body?.title ?? 'Terjadi kesalahan', body?.detail);
    }
    return routeOk(body?.data);
  } catch (error) {
    return routeError(error);
  }
}
