'use client';

import { ChevronLeft, ChevronRight } from 'lucide-react';
import type React from 'react';

import { cn } from '@/lib/utils';

export const PAGE_SIZE_OPTIONS = [10, 25, 50, 100] as const;

export type Column<T> = {
  key: string;
  label: string;
  /** Render kustom; default pakai row[key]. */
  render?: (row: T) => React.ReactNode;
  className?: string;
};

type Pagination = {
  page: number; // 1-based
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
  onPageSizeChange: (size: number) => void;
};

type DataTableProps<T> = {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string | number;
  loading?: boolean;
  /** Mode server-side: sediakan pagination. Bila tidak, tidak ada kontrol. */
  pagination?: Pagination;
  emptyText?: string;
  rowClassName?: (row: T) => string | undefined;
  renderRowActions?: (row: T) => React.ReactNode;
};

function defaultCell<T>(row: T, key: string): React.ReactNode {
  const v = (row as Record<string, unknown>)[key];
  if (v === null || v === undefined) return '-';
  if (Array.isArray(v)) return v.join(', ');
  if (typeof v === 'object') return JSON.stringify(v);
  return String(v);
}

export function DataTable<T>({
  columns,
  rows,
  rowKey,
  loading,
  pagination,
  emptyText = 'Belum ada data.',
  rowClassName,
  renderRowActions,
}: DataTableProps<T>) {
  const totalPages = pagination ? Math.max(1, Math.ceil(pagination.total / pagination.pageSize)) : 1;
  const page = pagination?.page ?? 1;

  return (
    <div className="admin-datatable">
      <div className="admin-table">
        <table>
          <thead>
            <tr>
              {columns.map((c) => (
                <th key={c.key} className={c.className}>
                  {c.label}
                </th>
              ))}
              {renderRowActions ? <th>Aksi</th> : null}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={rowKey(row)} className={rowClassName?.(row)}>
                {columns.map((c) => (
                  <td key={c.key} className={c.className}>
                    {c.render ? c.render(row) : defaultCell(row, c.key)}
                  </td>
                ))}
                {renderRowActions ? <td>{renderRowActions(row)}</td> : null}
              </tr>
            ))}
            {!loading && rows.length === 0 ? (
              <tr>
                <td colSpan={columns.length + (renderRowActions ? 1 : 0)} className="admin-table__empty">
                  {emptyText}
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      {pagination ? (
        <div className="admin-pagination">
          <div className="admin-pagination__size">
            <span>Baris per halaman</span>
            <select
              value={pagination.pageSize}
              onChange={(e) => pagination.onPageSizeChange(Number(e.target.value))}
              className="admin-inline-select"
            >
              {PAGE_SIZE_OPTIONS.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
          <div className="admin-pagination__info">
            {(page - 1) * pagination.pageSize + 1}–
            {Math.min(page * pagination.pageSize, pagination.total)} dari {pagination.total}
          </div>
          <div className="admin-pagination__nav">
            <button
              type="button"
              className={cn('admin-icon-btn', page <= 1 && 'is-disabled')}
              onClick={() => page > 1 && pagination.onPageChange(page - 1)}
              disabled={page <= 1}
              aria-label="Sebelumnya"
            >
              <ChevronLeft size={16} />
            </button>
            <span className="admin-pagination__page">
              {page} / {totalPages}
            </span>
            <button
              type="button"
              className={cn('admin-icon-btn', page >= totalPages && 'is-disabled')}
              onClick={() => page < totalPages && pagination.onPageChange(page + 1)}
              disabled={page >= totalPages}
              aria-label="Berikutnya"
            >
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
