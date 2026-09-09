import { formatRupiah } from '@rag-salon/shared-utils';
import { describe, expect, it } from 'vitest';
import { cn } from './utils';

describe('shared-utils via web', () => {
  it('formatRupiah menampilkan format Indonesia', () => {
    expect(formatRupiah(75000)).toMatch(/75\.000/);
  });
});

describe('cn', () => {
  it('menggabungkan kelas tailwind', () => {
    expect(cn('a', 'b')).toBe('a b');
  });
});
