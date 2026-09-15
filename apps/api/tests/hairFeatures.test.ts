import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import {
  buildHairFeatures,
  computeHairFeatureStats,
  hairColorLabel,
} from '../src/services/hairFeatures';

function loadFixture(): { rgb: Uint8Array; expected: Record<string, number> } {
  const raw = readFileSync(resolve(process.cwd(), 'tests/fixtures/hair_roi.raw'));
  const expected = JSON.parse(
    readFileSync(resolve(process.cwd(), 'tests/fixtures/hair_features.expected.json'), 'utf-8'),
  ) as Record<string, number>;
  return { rgb: new Uint8Array(raw.buffer, raw.byteOffset, raw.byteLength), expected };
}

describe('hairFeatures (port identik extract_features.py)', () => {
  it('menghitung statistik IDENTIK dengan Python untuk crop yang sama', () => {
    const { rgb, expected } = loadFixture();
    const W = 224;
    const H = 224;
    const stats = computeHairFeatureStats(rgb, W, H);

    const keys = Object.keys(expected);
    expect(keys.length).toBeGreaterThan(12);

    for (const key of keys) {
      const py = expected[key];
      const node = stats[key as keyof typeof stats];
      const diff = Math.abs(py - node);
      // toleransi kecil: perbedaan hanya dari pembulatan float (Python round 8 digit)
      expect(diff, `${key}: python=${py} node=${node}`).toBeLessThanOrEqual(1e-5);
    }
  });

  it('label warna mengikuti threshold kalibrasi', () => {
    expect(hairColorLabel(0.2, 0.3)).toBe('hitam');
    expect(hairColorLabel(0.9, 0.05)).toBe('pirang');
    expect(hairColorLabel(0.7, 0.3)).toBe('terang');
    expect(hairColorLabel(0.55, 0.3)).toBe('cokelat');
  });

  it('rule bleach & dry sesuai kalibrasi dataset', () => {
    const base = {
      H_min: 0,
      H_max: 0,
      H_p10: 0,
      H_median: 0,
      H_p90: 0,
      H_std: 0,
      S_mean: 0,
      S_std: 0,
      V_mean: 0,
      V_std: 0,
      V_p10: 0,
      V_p90: 0,
      dissimilarity: 0,
      homogeneity: 0,
      correlation: 0,
    };
    const low = buildHairFeatures({
      ...base,
      S_mean: 0.1,
      V_mean: 0.8,
      contrast: 2.0,
      energy: 0.2,
      entropy: 0.6,
    });
    expect(low.riskSigns?.bleach).toBe(true);

    const normal = buildHairFeatures({
      ...base,
      S_mean: 0.3,
      V_mean: 0.5,
      contrast: 4.0,
      energy: 0.15,
      entropy: 0.6,
    });
    expect(normal.riskSigns?.bleach).toBe(false);
    expect(normal.riskSigns?.dry).toBe(false);
    expect(normal.health).toBe('normal');

    const dry = buildHairFeatures({
      ...base,
      S_mean: 0.3,
      V_mean: 0.5,
      contrast: 9.0,
      energy: 0.02,
      entropy: 0.8,
    });
    expect(dry.riskSigns?.dry).toBe(true);
    expect(dry.health).toBe('kering');
  });
});
