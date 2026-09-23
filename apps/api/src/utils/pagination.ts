import type { Request } from 'express';

export interface PageParams {
  page: number;
  limit: number;
  offset: number;
  all: boolean;
}

const DEFAULT_LIMIT = 25;
const MAX_LIMIT = 200;

/** Baca page & limit dari query string (defaults + batas aman). */
export function pageParams(req: Request): PageParams {
  const all = req.query.all === '1' || req.query.all === 'true';
  const page = Math.max(1, Number(req.query.page ?? 1) || 1);
  const limitRaw = Number(req.query.limit ?? DEFAULT_LIMIT) || DEFAULT_LIMIT;
  const limit = Math.min(MAX_LIMIT, Math.max(1, limitRaw));
  return { page, limit, offset: (page - 1) * limit, all };
}

/** True bila klien meminta format paginasi (page/limit/all dikirim). */
export function wantsPaged(req: Request): boolean {
  return (
    req.query.page !== undefined || req.query.limit !== undefined || req.query.all !== undefined
  );
}

/**
 * Bungkus hasil paging.
 * Bila `all` = true -> kembalikan seluruh item (untuk dropdown).
 */
export function paged<T>(allRows: T[], total: number, p: PageParams) {
  if (p.all) {
    return { items: allRows, total: allRows.length, page: 1, limit: allRows.length };
  }
  return {
    items: allRows.slice(p.offset, p.offset + p.limit),
    total,
    page: p.page,
    limit: p.limit,
  };
}

/**
 * Backward-compatible: kembalikan array biasa bila klien TIDAK meminta
 * paginasi; kembalikan objek {items,total,...} bila meminta.
 */
export function pagedOrArray<T>(req: Request, allRows: T[]) {
  if (!wantsPaged(req)) return allRows;
  return paged(allRows, allRows.length, pageParams(req));
}
