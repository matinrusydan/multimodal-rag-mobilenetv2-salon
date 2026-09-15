import type { HairFeatures } from '@rag-salon/shared-types';

/**
 * Hair features (Opsi 3 hibrida — HSV stats + GLCM), port IDENTIK dari
 * `cv/scripts/extract_features.py` (Python). Nilai runtime harus sama dengan
 * hasil analisis Python untuk citra yang sama.
 *
 * - ROI: crop 224x224 RGB yang SAMA dengan preprocessing inference (CvService.#preprocess).
 * - RGB -> HSV float64 manual (0..360 deg), luma Y' = 0.299R + 0.587G + 0.114B.
 * - GLCM: 4 arah (0,45,90,135 deg), levels=32, symmetric + normed, lalu
 *   graycoprops (contrast/dissimilarity/homogeneity/energy/correlation)
 *   + entropy ternormalisasi.
 * - Threshold rule dikalibrasi dari `cv/reports/hair_features_report.json`
 *   (figaro1k, n=600) — lihat `_rulesFromReport`.
 */

export const GLCM_LEVELS = 32;
const GLCM_ANGLES = [0, Math.PI / 4, Math.PI / 2, (3 * Math.PI) / 4];
const GLCM_DIST = 1;

interface RuleThresholds {
  /** bleach: S_mean < sLow AND V_mean >= vHigh  (S_p10 & V_p90 from dataset) */
  bleachS: number;
  bleachV: number;
  /** dry: contrast >= dryContrast OR energy <= dryEnergy (contrast_p90 & energy_p10) */
  dryContrast: number;
  dryEnergy: number;
  /** texture bins by GLCM contrast quartiles */
  textureQ1: number;
  textureQ3: number;
}

/** Kalibrasi dari cv/reports/hair_features_report.json (overall, n=600). */
const RULES: RuleThresholds = {
  bleachS: 0.1815,
  bleachV: 0.7072,
  dryContrast: 7.7774,
  dryEnergy: 0.098,
  textureQ1: 2.9138,
  textureQ3: 5.5236,
};

export interface HairFeatureStats {
  H_min: number;
  H_max: number;
  H_p10: number;
  H_median: number;
  H_p90: number;
  H_std: number;
  S_mean: number;
  S_std: number;
  V_mean: number;
  V_std: number;
  V_p10: number;
  V_p90: number;
  contrast: number;
  dissimilarity: number;
  homogeneity: number;
  energy: number;
  correlation: number;
  entropy: number;
}

function percentile(sorted: Float64Array, p: number): number {
  if (sorted.length === 0) return 0;
  const idx = (sorted.length - 1) * p;
  const lo = Math.floor(idx);
  const hi = Math.ceil(idx);
  if (lo === hi) return sorted[lo];
  const frac = idx - lo;
  return sorted[lo] + (sorted[hi] - sorted[lo]) * frac;
}

/** `round(x, 4)` ala Python (ke 4 desimal, half-to-even via Math.round cukup sini). */
function round4(x: number): number {
  return Math.round(x * 1e4) / 1e4;
}

/** Banker's rounding identik `np.round` (half-to-even). */
function npRound(x: number): number {
  const r = Math.round(x);
  return Math.abs(x % 1) === 0.5 ? (r % 2 === 0 ? r : r - Math.sign(x)) : r;
}

function stdDev(xs: Float64Array, mean: number): number {
  let acc = 0;
  for (let i = 0; i < xs.length; i++) {
    const d = xs[i] - mean;
    acc += d * d;
  }
  return Math.sqrt(acc / xs.length);
}

/** RGB (0..255) -> H (0..360), S (0..1), V (0..1). Formula identik Python `_rgb_to_hsv`. */
function rgbToHsv(r: number, g: number, b: number): [number, number, number] {
  const rf = r / 255;
  const gf = g / 255;
  const bf = b / 255;
  const v = Math.max(rf, gf, bf);
  const mn = Math.min(rf, gf, bf);
  const diff = v - mn;
  const s = diff === 0 ? 0 : diff / v;
  let h = 0;
  if (diff > 0) {
    if (v === rf) h = 60 * mod6((gf - bf) / diff);
    else if (v === gf) h = 60 * ((bf - rf) / diff + 2);
    else h = 60 * ((rf - gf) / diff + 4);
  }
  return [h, s, v];
}

/** Python `%` (modulus selalu non-negatif). */
function mod6(x: number): number {
  return ((x % 6) + 6) % 6;
}

function buildGlcmForAngle(
  q: Uint8Array,
  width: number,
  height: number,
  dr: number,
  dc: number,
): Float64Array {
  const P = new Float64Array(GLCM_LEVELS * GLCM_LEVELS);
  for (let r = 0; r < height; r++) {
    const nr = r + dr;
    if (nr < 0 || nr >= height) continue;
    for (let c = 0; c < width; c++) {
      const nc = c + dc;
      if (nc < 0 || nc >= width) continue;
      const i = q[r * width + c];
      const j = q[nr * width + nc];
      P[i * GLCM_LEVELS + j] += 1;
    }
  }
  return P;
}

/** GLCM symmetric + normed (identik skimage graycomatrix). Returns per-angle Float64Array. */
function glcmSymmetricNormed(q: Uint8Array, width: number, height: number): Float64Array[] {
  const mats = GLCM_ANGLES.map((ang) => {
    const dr = Math.round(Math.sin(ang) * GLCM_DIST);
    const dc = Math.round(Math.cos(ang) * GLCM_DIST);
    return buildGlcmForAngle(q, width, height, dr, dc);
  });
  for (const P of mats) {
    for (let i = 0; i < GLCM_LEVELS; i++) {
      for (let j = i + 1; j < GLCM_LEVELS; j++) {
        const a = P[i * GLCM_LEVELS + j];
        const b = P[j * GLCM_LEVELS + i];
        P[i * GLCM_LEVELS + j] = a + b;
        P[j * GLCM_LEVELS + i] = a + b;
      }
    }
    // skimage symmetric: P = P + P.T -> diagonal turut digandakan.
    for (let i = 0; i < GLCM_LEVELS; i++) {
      P[i * GLCM_LEVELS + i] *= 2;
    }
    let sum = 0;
    for (let k = 0; k < P.length; k++) sum += P[k];
    if (sum === 0) sum = 1;
    for (let k = 0; k < P.length; k++) P[k] /= sum;
  }
  return mats;
}

/** graycoprops per angle (identik skimage graycoprops) + entropy of mean matrix. */
function glcmProps(
  mats: Float64Array[],
): Omit<
  HairFeatureStats,
  | 'H_min'
  | 'H_max'
  | 'H_p10'
  | 'H_median'
  | 'H_p90'
  | 'H_std'
  | 'S_mean'
  | 'S_std'
  | 'V_mean'
  | 'V_std'
  | 'V_p10'
  | 'V_p90'
> {
  const accum = { contrast: 0, dissimilarity: 0, homogeneity: 0, energy: 0, correlation: 0 };
  const pFlat = new Float64Array(GLCM_LEVELS * GLCM_LEVELS);

  for (const P of mats) {
    // graycoprops re-normalisasi dulu (sum≈1 setelah normed, tapi koreksi ulang)
    let total = 0;
    for (let k = 0; k < P.length; k++) total += P[k];
    if (total === 0) total = 1;
    const p = new Float64Array(GLCM_LEVELS * GLCM_LEVELS);
    for (let k = 0; k < P.length; k++) {
      const v = P[k] / total;
      p[k] = v;
      pFlat[k] += v / mats.length;
    }

    let contrast = 0;
    let dissimilarity = 0;
    let homogeneity = 0;
    let energy = 0;
    let meanI = 0;
    let meanJ = 0;
    for (let i = 0; i < GLCM_LEVELS; i++) {
      for (let j = 0; j < GLCM_LEVELS; j++) {
        const v = p[i * GLCM_LEVELS + j];
        const d = i - j;
        contrast += v * d * d;
        dissimilarity += v * Math.abs(d);
        homogeneity += v / (1 + d * d);
        energy += v * v;
        meanI += i * v;
        meanJ += j * v;
      }
    }
    let stdI = 0;
    let stdJ = 0;
    let cov = 0;
    for (let i = 0; i < GLCM_LEVELS; i++) {
      for (let j = 0; j < GLCM_LEVELS; j++) {
        const v = p[i * GLCM_LEVELS + j];
        const di = i - meanI;
        const dj = j - meanJ;
        stdI += v * di * di;
        stdJ += v * dj * dj;
        cov += v * di * dj;
      }
    }
    stdI = Math.sqrt(stdI);
    stdJ = Math.sqrt(stdJ);
    const correlation = stdI < 1e-15 || stdJ < 1e-15 ? 1 : cov / (stdI * stdJ);

    accum.contrast += contrast;
    accum.dissimilarity += dissimilarity;
    accum.homogeneity += homogeneity;
    accum.energy += Math.sqrt(energy);
    accum.correlation += correlation;
  }

  // entropy dari RATA-RATA matriks (p_flat = mean over angles), lalu norm /log2(levels^2).
  let ent = 0;
  for (const v of pFlat) {
    if (v > 0) ent += v * Math.log2(v);
  }

  const n = mats.length;
  return {
    contrast: accum.contrast / n,
    dissimilarity: accum.dissimilarity / n,
    homogeneity: accum.homogeneity / n,
    energy: accum.energy / n,
    correlation: accum.correlation / n,
    entropy: round4(-ent / Math.log2(GLCM_LEVELS * GLCM_LEVELS)),
  };
}

/** Hitung hair features dari crop RGB 224x224 (raw interleaved R,G,B). */
export function computeHairFeatureStats(
  rgb: Uint8Array,
  width: number,
  height: number,
): HairFeatureStats {
  const count = width * height;
  const hue = new Float64Array(count);
  const sat = new Float64Array(count);
  const val = new Float64Array(count);
  const gray = new Uint8Array(count);

  for (let i = 0; i < count; i++) {
    const r = rgb[i * 3];
    const g = rgb[i * 3 + 1];
    const b = rgb[i * 3 + 2];
    const [h, s, v] = rgbToHsv(r, g, b);
    hue[i] = h;
    sat[i] = s;
    val[i] = v;
    gray[i] = npRound(0.299 * r + 0.587 * g + 0.114 * b);
  }

  const hueSorted = Float64Array.from(hue).sort();
  const valSorted = Float64Array.from(val).sort();

  // q = clip(floor(val * levels / 255), 0, levels-1) — identik numpy int64 cast + clip.
  const q = new Uint8Array(count);
  for (let i = 0; i < count; i++) {
    const qv = Math.floor((gray[i] * GLCM_LEVELS) / 255);
    q[i] = qv < 0 ? 0 : qv > GLCM_LEVELS - 1 ? GLCM_LEVELS - 1 : qv;
  }

  const glcm = glcmProps(glcmSymmetricNormed(q, width, height));

  const satMean = sat.reduce((a, b) => a + b, 0) / count;
  const valMean = val.reduce((a, b) => a + b, 0) / count;
  const hueMean = hue.reduce((a, b) => a + b, 0) / count;

  return {
    H_min: hueSorted[0],
    H_max: hueSorted[hueSorted.length - 1],
    H_p10: percentile(hueSorted, 0.1),
    H_median: percentile(hueSorted, 0.5),
    H_p90: percentile(hueSorted, 0.9),
    H_std: stdDev(hue, hueMean),
    S_mean: satMean,
    S_std: stdDev(sat, satMean),
    V_mean: valMean,
    V_std: stdDev(val, valMean),
    V_p10: percentile(valSorted, 0.1),
    V_p90: percentile(valSorted, 0.9),
    ...glcm,
  };
}

/** Label warna kasar — port dari Python `_color_label`. */
export function hairColorLabel(vMean: number, sMean: number): string {
  if (vMean < 0.25) return 'hitam';
  if (vMean < 0.45) return sMean > 0.15 ? 'gelap' : 'abu-gelap';
  if (vMean < 0.65) return sMean > 0.15 ? 'cokelat' : 'abu';
  if (vMean < 0.85) {
    if (sMean > 0.18) return 'terang';
    return sMean < 0.1 ? 'pirang' : 'cokelat-terang';
  }
  return sMean < 0.12 ? 'pirang' : 'terang';
}

/** Aturan rule (kalibrasi report) -> HairFeatures untuk konteks RAG. */
export function buildHairFeatures(stats: HairFeatureStats): HairFeatures {
  const bleach = stats.S_mean < RULES.bleachS && stats.V_mean >= RULES.bleachV;
  const dry = stats.contrast >= RULES.dryContrast || stats.energy <= RULES.dryEnergy;
  let texture = 'halus';
  if (stats.contrast >= RULES.textureQ3) texture = 'kasar';
  else if (stats.contrast >= RULES.textureQ1) texture = 'sedang';
  return {
    color: hairColorLabel(stats.V_mean, stats.S_mean),
    texture,
    health: dry ? 'kering' : 'normal',
    riskSigns: { bleach, dry },
  };
}

/** Satu panggilan lengkap untuk CvService. */
export function computeHairFeatures(rgb: Uint8Array, width: number, height: number): HairFeatures {
  return buildHairFeatures(computeHairFeatureStats(rgb, width, height));
}
