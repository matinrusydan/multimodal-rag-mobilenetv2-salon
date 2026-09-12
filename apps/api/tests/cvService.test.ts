import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it, vi } from 'vitest';

vi.mock('../src/config/env', () => ({
  env: {
    CONFIDENCE_THRESHOLD: 0.6,
    MODEL_TYPE_PATH: './cv/weights/hair_type.onnx',
    MODEL_LENGTH_PATH: './cv/weights/hair_length.onnx',
  },
}));

vi.mock('../src/config/logger', () => ({
  logger: { info: vi.fn(), warn: vi.fn(), debug: vi.fn() },
}));

// dynamic import SETELAH mock env terpasang
const { CvService } = await import('../src/services/CvService');

describe('CvService (hair_type ONNX)', () => {
  it('mengklasifikasikan citra lurus nyata dari dataset', async () => {
    const svc = new CvService();
    await svc.load();
    const imgPath = resolve(process.cwd(), 'cv/dataset/figaro1k/lurus/00057.jpg');
    const result = await svc.analyze(readFileSync(imgPath));
    expect(result.hairType.label).toBe('lurus');
    expect(result.hairType.confidence).toBeGreaterThan(0);
    expect(result.hairType.confidence).toBeLessThanOrEqual(1);
    expect(result.hairLength.label).toBe('menengah');
    expect(result.status).toMatch(/^(ok|low_confidence)$/);
  });

  it('menolak buffer gambar yang tidak valid', async () => {
    const svc = new CvService();
    await svc.load();
    const bogus = Buffer.from('ini bukan gambar sama sekali');
    await expect(svc.analyze(bogus)).rejects.toThrow();
  });

  it('menandai low_confidence bila model tidak dimuat (fallback 0.5 < threshold 0.6)', async () => {
    const svc = new CvService(); // tanpa load() -> typeSession null -> fallback conf 0.5
    const noModel = svc.analyze(Buffer.from('x'));
    // analyze tanpa session TIDAK melempar; hasil fallback
    const result = await noModel;
    expect(result.status).toBe('low_confidence');
    expect(result.hairType.confidence).toBeLessThan(0.6);
    expect(result.hairLength.confidence).toBeLessThan(0.6);
  });
});
