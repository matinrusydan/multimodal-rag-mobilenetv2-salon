import type { Request, Response } from 'express';
import { cvService } from '../services/CvService';
import { HttpError, sendProblem } from '../utils/problemDetails';
import { ok } from '../utils/response';

export async function analyze(req: Request, res: Response): Promise<void> {
  if (!req.file) {
    sendProblem(
      res,
      { title: 'Gambar diperlukan', detail: 'Unggah satu gambar rambut (JPG/PNG/WebP)' },
      400,
    );
    return;
  }

  const mimetypeOk = ['image/jpeg', 'image/png', 'image/webp'].includes(req.file.mimetype);
  if (!mimetypeOk) {
    throw new HttpError(400, 'Format gambar harus JPG, PNG, atau WebP');
  }

  const result = await cvService.analyze(req.file.buffer);
  ok(res, result);
}
