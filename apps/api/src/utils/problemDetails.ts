import type { Response } from 'express';

export interface ProblemDetails {
  type: string;
  title: string;
  status: number;
  detail: string;
  instance?: string;
}

export function sendProblem(
  res: Response,
  details: Omit<ProblemDetails, 'type' | 'status'>,
  status: number,
): void {
  const body: ProblemDetails = {
    type: `about:blank#${status}`,
    title: details.title ?? getTitle(status),
    status,
    detail: details.detail,
  };
  res.status(status).json(body);
}

export class HttpError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = 'HttpError';
  }
}

function getTitle(status: number): string {
  switch (status) {
    case 400:
      return 'Permintaan tidak valid';
    case 401:
      return 'Tidak terautentikasi';
    case 403:
      return 'Akses ditolak';
    case 404:
      return 'Tidak ditemukan';
    case 429:
      return 'Terlalu banyak permintaan';
    case 500:
      return 'Kesalahan server';
    default:
      return 'Terjadi kesalahan';
  }
}
