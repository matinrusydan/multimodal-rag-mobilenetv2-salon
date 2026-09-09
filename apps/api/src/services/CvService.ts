import type {
  AnalyzeResponse,
  ClassificationResult,
  HairLengthLabel,
  HairTypeLabel,
} from '@rag-salon/shared-types';

/**
 * STUB — implementasi penuh (MobileNetV2 → ONNX → onnxruntime-node) di Phase 07.
 */
export class CvService {
  async analyze(_buffer: Buffer): Promise<AnalyzeResponse> {
    const hairLength: ClassificationResult = {
      label: 'menengah' as HairLengthLabel,
      confidence: 0.92,
    };
    const hairType: ClassificationResult = {
      label: 'bergelombang' as HairTypeLabel,
      confidence: 0.87,
    };
    return {
      hairLength,
      hairType,
      analyzedAt: new Date().toISOString(),
      status: 'ok',
    };
  }
}

export const cvService = new CvService();
