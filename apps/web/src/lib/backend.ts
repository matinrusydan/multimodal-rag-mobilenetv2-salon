import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL ?? 'http://127.0.0.1:4000';

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public detail?: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export function problem(status: number, title: string, detail?: string) {
  return new ApiError(status, title, detail);
}

type BackendInit = RequestInit & { token?: string };

export async function backendRequest<T>(path: string, init: BackendInit = {}): Promise<T> {
  const { token, ...requestInit } = init;
  const headers: Record<string, string> = {
    ...(requestInit.headers as Record<string, string> | undefined),
    accept: 'application/json',
  };
  if (requestInit.body !== undefined && requestInit.body !== null) {
    headers['content-type'] = 'application/json';
  }
  if (token) {
    headers.authorization = `Bearer ${token}`;
  }

  const res = await fetch(`${BACKEND_URL}/api${path}`, {
    ...requestInit,
    headers,
    cache: 'no-store',
  });

  const body = (await res.json().catch(() => null)) as {
    ok: boolean;
    data?: T;
    title?: string;
    detail?: string;
  } | null;

  if (!res.ok) {
    throw new ApiError(res.status, body?.title ?? 'Terjadi kesalahan', body?.detail);
  }

  return body?.data as T;
}

export function routeError(error: unknown) {
  if (error instanceof ApiError) {
    return NextResponse.json(
      {
        type: `about:blank#${error.status}`,
        title: error.message,
        status: error.status,
        detail: error.detail,
      },
      { status: error.status },
    );
  }
  return NextResponse.json(
    {
      type: 'about:blank#500',
      title: 'Kesalahan server',
      status: 500,
      detail: 'Terjadi kesalahan internal',
    },
    { status: 500 },
  );
}

export function routeOk(data: unknown, status = 200) {
  return NextResponse.json({ ok: true, data }, { status });
}
