import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import type {
  AnalyzeResponse,
  ClassificationResult,
  HairFeatures,
  HairLengthLabel,
  HairTypeLabel,
} from '@rag-salon/shared-types';
import * as ort from 'onnxruntime-node';
import sharp from 'sharp';
import { env } from '../config/env';
import { logger } from '../config/logger';
import { computeHairFeatures } from './hairFeatures';

/** Preprocessing inference: IDENTIK dengan training val (task 07-cv.md §3). */
const RESIZE_SIDE = 256;
const CROP = 224;
const IMAGENET_MEAN: readonly number[] = [0.485, 0.456, 0.406];
const IMAGENET_STD: readonly number[] = [0.229, 0.224, 0.225];

const HAIR_TYPE_LABELS: readonly HairTypeLabel[] = [
  'lurus',
  'bergelombang',
  'keriting',
  'sangat-keriting',
];

const HAIR_LENGTH_LABELS: readonly HairLengthLabel[] = [
  'pendek',
  'pendek-menengah',
  'menengah',
  'panjang',
];

/**
 * Computer Vision via MobileNetV2 -> ONNX -> onnxruntime-node.
 * - hair_type.onnx  : model REAL (di-train dari figaro1k, 4 kelas jenis rambut).
 * - hair_length.onnx: belum tersedia (dataset panjang rambut belum ada) =>
 *   fallback label 'menengah' ber-confiden rendah; status jadi low_confidence.
 */
export class CvService {
  private typeSession: ort.InferenceSession | null = null;
  private readonly threshold = env.CONFIDENCE_THRESHOLD;

  private typePath(): string {
    return resolve(process.cwd(), env.MODEL_TYPE_PATH);
  }

  async load(): Promise<void> {
    const typePath = this.typePath();
    if (existsSync(typePath)) {
      this.typeSession = await ort.InferenceSession.create(readFileSync(typePath), {
        executionProviders: ['cpu'],
      });
      logger.info({ model: typePath }, 'CvService.hair_type ONNX dimuat');
    } else {
      logger.warn(
        { model: typePath },
        'MODEL_TYPE_PATH tidak ada; hair_type pakai fallback low_confidence',
      );
    }
  }

  async analyze(buffer: Buffer): Promise<AnalyzeResponse> {
    const t0 = Date.now();
    let hairType: ClassificationResult;
    let hairFeatures: HairFeatures | undefined;

    if (this.typeSession) {
      const { tensor, rgb } = await this.#preprocess(buffer);
      hairType = await this.#runType(tensor);
      hairFeatures = computeHairFeatures(rgb, CROP, CROP);
    } else {
      hairType = { label: 'bergelombang' as HairTypeLabel, confidence: 0.5 };
    }

    // hair_length belum punya model ONNX => fallback rendah (pending dataset labeled)
    const hairLength: ClassificationResult = {
      label: 'menengah' as HairLengthLabel,
      confidence: 0.5,
    };

    // fallback hair_length (conf 0.5) harus rendah walau conf == threshold (prod 0.5)
    const lowLength = hairLength.confidence <= this.threshold;
    const lowType = hairType.confidence < this.threshold;
    const status: AnalyzeResponse['status'] = lowLength || lowType ? 'low_confidence' : 'ok';

    logger.debug(
      { hairType, hairLength, hairFeatures, elapsedMs: Date.now() - t0 },
      'CvService.analyze selesai',
    );
    return {
      hairLength,
      hairType,
      hairFeatures,
      analyzedAt: new Date().toISOString(),
      status,
    };
  }

  /** Preprocess tunggal: cropping RGB (untuk hair features) + tensor NCHW (inference). */
  async #preprocess(buffer: Buffer): Promise<{ tensor: ort.Tensor; rgb: Uint8Array }> {
    const img = sharp(buffer).rotate().toColourspace('srgb').removeAlpha();
    const meta = await img.metadata();
    const w = meta.width ?? 0;
    const h = meta.height ?? 0;
    if (w === 0 || h === 0) {
      throw new Error('Gambar tidak dapat dibaca');
    }
    const scale = RESIZE_SIDE / Math.min(w, h);
    const rw = Math.max(CROP, Math.round(w * scale));
    const rh = Math.max(CROP, Math.round(h * scale));
    const left = Math.floor((rw - CROP) / 2);
    const top = Math.floor((rh - CROP) / 2);

    const resized = await img
      .resize(rw, rh, { fit: 'fill' })
      .extract({ left, top, width: CROP, height: CROP })
      .raw()
      .toBuffer({ resolveWithObject: true });

    const { data } = resized;
    const rgb = new Uint8Array(data.buffer, data.byteOffset, CROP * CROP * 3);

    const count = CROP * CROP;
    // NCHW: channels R, G, B masing-masing contiguous 224x224
    const out = new Float32Array(3 * count);
    let n = 0;
    for (let i = 0; i < count; i++) {
      for (let c = 0; c < 3; c++) {
        const val = data[n++] / 255;
        out[c * count + i] = (val - IMAGENET_MEAN[c]) / IMAGENET_STD[c];
      }
    }
    return { tensor: new ort.Tensor('float32', out, [1, 3, CROP, CROP]), rgb };
  }

  /** Inference tunggal dari tensor NCHW (hasil #preprocess). */
  async #runType(tensor: ort.Tensor): Promise<ClassificationResult> {
    const feeds: Record<string, ort.Tensor> = { input: tensor };
    const result = (await this.typeSession?.run(feeds)) as { logits: ort.Tensor };
    const output = (result?.logits?.data as Float32Array | undefined) ?? new Float32Array(0);
    if (output.length === 0) {
      throw new Error('Output ONNX hair_type kosong');
    }
    const probs = this.#softmax(output);
    const idx = probs.indexOf(Math.max(...probs));
    return {
      label: HAIR_TYPE_LABELS[idx] as HairTypeLabel,
      confidence: Number(probs[idx].toFixed(4)),
    };
  }

  #softmax(logits: Float32Array): number[] {
    const max = Math.max(...logits);
    const exps = Array.from(logits, (v) => Math.exp(v - max));
    const sum = exps.reduce((a, b) => a + b, 0);
    return exps.map((v) => v / sum);
  }
}

export const cvService: CvService = new CvService();

/** Panggil sekali saat bootstrap (app.ts) supaya session tersedia sebelum request. */
export function initCvService(): void {
  void cvService.load();
}
