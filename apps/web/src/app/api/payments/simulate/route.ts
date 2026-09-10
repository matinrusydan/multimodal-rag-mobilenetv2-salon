import type { NextRequest } from 'next/server';

import { backendRequest, problem, routeError, routeOk } from '@/lib/backend';
import { getSession } from '@/lib/web-session';
import type { PaymentMethod } from '@rag-salon/shared-types';

export async function POST(request: NextRequest) {
  try {
    const session = await getSession();
    if (!session) {
      return routeError(problem(401, 'Tidak terautentikasi', 'Silakan masuk terlebih dahulu.'));
    }
    const body = (await request.json()) as { reservationId?: string; method?: PaymentMethod };
    if (!body.reservationId || !body.method) {
      return routeError(
        problem(400, 'Permintaan tidak valid', 'ID reservasi dan metode pembayaran wajib diisi.'),
      );
    }
    const data = await backendRequest('/payments/simulate', {
      method: 'POST',
      token: session.token,
      body: JSON.stringify({ reservationId: body.reservationId, method: body.method }),
    });
    return routeOk(data);
  } catch (error) {
    return routeError(error);
  }
}
