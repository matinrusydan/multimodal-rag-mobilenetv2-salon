import { describe, expect, it } from 'vitest';
import { embedLocal } from '../../src/rag/embedding';

describe('embedding local (offline)', () => {
  it('menghasilkan vektor 1536d yang sama untuk input identik', () => {
    const a = embedLocal(['harga potong rambut']);
    const b = embedLocal(['harga potong rambut']);
    expect(a[0]).toHaveLength(1536);
    expect(a[0]).toEqual(b[0]);
  });

  it('teks mirip memiliki jarak lebih kecil dari teks berbeda', () => {
    const [a1, a2, b] = embedLocal([
      'berapa harga potong rambut pria',
      'harga layanan potong rambut',
      'cara merawat rambut keriting',
    ]);
    const dotA = a1.reduce((s, v, i) => s + v * a2[i], 0);
    const dotB = a1.reduce((s, v, i) => s + v * b[i], 0);
    expect(dotA).toBeGreaterThan(dotB);
  });
});
