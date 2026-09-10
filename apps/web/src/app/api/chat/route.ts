import type { NextRequest } from 'next/server';

import { backendRequest, problem, routeError, routeOk } from '@/lib/backend';

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as {
      message?: string;
      hairContext?: unknown;
      contextId?: string;
    };
    if (!body.message) {
      return routeError(problem(400, 'Permintaan tidak valid', 'Pesan wajib diisi.'));
    }
    const data = await backendRequest('/chat', {
      method: 'POST',
      body: JSON.stringify({
        message: body.message,
        hairContext: body.hairContext,
        contextId: body.contextId,
      }),
    });
    return routeOk(data);
  } catch (error) {
    return routeError(error);
  }
}
