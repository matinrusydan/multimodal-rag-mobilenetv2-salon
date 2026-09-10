import type { NextRequest } from 'next/server';

import { backendRequest, problem, routeError, routeOk } from '@/lib/backend';
import { getSession } from '@/lib/web-session';

export async function GET() {
  try {
    const session = await getSession();
    if (!session) {
      return routeError(problem(401, 'Tidak terautentikasi', 'Silakan masuk terlebih dahulu.'));
    }
    const data = await backendRequest('/reservations', { token: session.token });
    return routeOk(data);
  } catch (error) {
    return routeError(error);
  }
}

export async function POST(request: NextRequest) {
  try {
    const session = await getSession();
    if (!session) {
      return routeError(problem(401, 'Tidak terautentikasi', 'Silakan masuk terlebih dahulu.'));
    }
    const body = (await request.json()) as {
      serviceIds?: number[];
      date?: string;
      time?: string;
      notes?: string;
    };
    if (!body.serviceIds?.length || !body.date || !body.time) {
      return routeError(
        problem(400, 'Permintaan tidak valid', 'Layanan, tanggal, dan jam wajib diisi.'),
      );
    }
    const data = await backendRequest('/reservations', {
      method: 'POST',
      token: session.token,
      body: JSON.stringify({
        serviceIds: body.serviceIds,
        date: body.date,
        time: body.time,
        notes: body.notes,
      }),
    });
    return routeOk(data, 201);
  } catch (error) {
    return routeError(error);
  }
}
