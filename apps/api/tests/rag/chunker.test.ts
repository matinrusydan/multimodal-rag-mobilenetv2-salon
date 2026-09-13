import { describe, expect, it } from 'vitest';
import { chunkMarkdown, estimateTokens, splitSections } from '../../src/rag/chunker';

const doc = `
# Judul

## Harga Potong

Konsultasi singkat, shaping presisi, dan styling akhir agar potongan rapi.
Harga Rp 220.000, durasi 60 menit. Cocok untuk refresh style.

## Harga Cream Bath

Masker rambut bernutrisi, relaksasi kulit kepala. Harga Rp 325.000.
Melembapkan rambut kering dan mengurangi rambut kusut.
`;

describe('chunker', () => {
  it('memisahkan markdown per section (##)', () => {
    const sections = splitSections(doc);
    expect(sections).toHaveLength(2);
    expect(sections[0].header).toBe('Harga Potong');
    expect(sections[1].header).toBe('Harga Cream Bath');
  });

  it('menghasilkan chunk dengan estimasi token <= maxTokens', () => {
    const chunks = chunkMarkdown(doc.repeat(30), { maxTokens: 200 });
    expect(chunks.length).toBeGreaterThan(1);
    for (const c of chunks) {
      expect(estimateTokens(c.text)).toBeLessThanOrEqual(210);
    }
  });

  it('tidak memotong di tengah kalimat (setiap chunk berakhir dengan tanda baca titik)', () => {
    const longText = `Ini adalah kalimat pertama yang cukup panjang. ${'Kalimat kedua juga panjang. '.repeat(200)}`;
    const chunks = chunkMarkdown(`## Bagian\n\n${longText}`, { maxTokens: 200 });
    for (const c of chunks) {
      expect(c.text.endsWith('.')).toBe(true);
    }
  });

  it('overlap antar chunk berurutan membawa isi chunk sebelumnya', () => {
    const longText = 'Kata berulang di tengah sangat khusus. '.repeat(120);
    const chunks = chunkMarkdown(`## Bagian\n\n${longText}`, {
      maxTokens: 300,
      minTokens: 100,
      overlapTokens: 25,
    });
    expect(chunks.length).toBeGreaterThan(1);
    // Isi bagian akhir chunk[0] muncul di chunk[1] (overlap).
    const tail = chunks[0].text.slice(-40);
    expect(chunks[1].text.slice(0, 60)).toContain(tail.slice(0, 20));
  });

  it('dokumen tanpa section menghasilkan fallback chunks', () => {
    const chunks = chunkMarkdown('Tanpa heading sama sekali. '.repeat(400));
    expect(chunks.length).toBeGreaterThan(0);
    expect(chunks[0].section).toBe('Dokumen');
  });
});
