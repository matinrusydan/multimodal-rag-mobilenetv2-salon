import type { NextRequest } from 'next/server';

import { ApiError, problem, routeError, routeOk } from '@/lib/backend';
import { getSession } from '@/lib/web-session';

const BACKEND_URL = process.env.BACKEND_URL ?? 'http://127.0.0.1:4000';

export const maxDuration = 120;

type RouteContext = {
  params: Promise<{ path: string[] }>;
};

async function forward(request: NextRequest, path: string[], method: string) {
  try {
    const session = await getSession();
    if (!session) {
      return routeError(problem(401, 'Tidak terautentikasi', 'Silakan masuk terlebih dahulu.'));
    }

    const search = request.nextUrl.search ?? '';
    const target = `${BACKEND_URL}/api/${path.join('/')}${search}`;
    const headers: HeadersInit = {
      accept: 'application/json',
      authorization: `Bearer ${session.token}`,
    };

    let body: BodyInit | null | undefined;
    const contentType = request.headers.get('content-type') ?? '';
    if (contentType.includes('multipart/form-data')) {
      body = await request.formData();
    } else if (contentType.includes('application/json')) {
      const text = await request.text();
      if (text) {
        body = text;
        headers['content-type'] = 'application/json';
      }
    }

    const signal = path[0] === 'agent' ? AbortSignal.timeout(100_000) : undefined;
    const res = await fetch(target, {
      method,
      headers,
      body,
      signal,
      cache: 'no-store',
    });
    const responseBody = (await res.json().catch(() => {
      if (signal?.aborted) throw signal.reason;
      return null;
    })) as {
      ok?: boolean;
      data?: unknown;
      title?: string;
      detail?: string;
      errors?: unknown;
    } | null;

    if (!res.ok) {
      throw new ApiError(
        res.status,
        responseBody?.title ?? 'Terjadi kesalahan',
        responseBody?.detail,
      );
    }
    return routeOk(responseBody?.data ?? null);
  } catch (error) {
    return routeError(error);
  }
}

export async function GET(request: NextRequest, { params }: RouteContext) {
  const { path } = await params;
  return forward(request, path, 'GET');
}

export async function POST(request: NextRequest, { params }: RouteContext) {
  const { path } = await params;
  return forward(request, path, 'POST');
}

export async function PUT(request: NextRequest, { params }: RouteContext) {
  const { path } = await params;
  return forward(request, path, 'PUT');
}

export async function DELETE(request: NextRequest, { params }: RouteContext) {
  const { path } = await params;
  return forward(request, path, 'DELETE');
}
