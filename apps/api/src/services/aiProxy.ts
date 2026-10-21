import { env } from '../config/env';
import { logger } from '../config/logger';
import { HttpError } from '../utils/problemDetails';

/** Fetch the AI envelope without exposing upstream bodies, credentials, or network errors. */
export async function requestAi(
  path: string,
  options: RequestInit,
  timeoutMs: number,
): Promise<object> {
  const started = Date.now();
  const signal = AbortSignal.timeout(timeoutMs);
  let status: number | undefined;
  let outcome = 'network';

  try {
    const res = await fetch(`${env.AI_URL}/ai${path}`, {
      ...options,
      signal,
      // Never forward the internal token to a redirect destination.
      redirect: 'error',
    });
    status = res.status;
    if (!res.ok) {
      outcome = 'upstream';
      // Do not consume or log error bodies: they may contain secrets or internal tracebacks.
      await res.body?.cancel().catch(() => undefined);
      const publicStatus = status === 504 ? 504 : status >= 500 ? 502 : status;
      throw new HttpError(publicStatus, 'Layanan AI gagal memproses permintaan. Silakan coba lagi.');
    }

    outcome = 'invalid-response';
    const json: unknown = await res.json();
    if (
      !json ||
      typeof json !== 'object' ||
      !('data' in json) ||
      !json.data ||
      typeof json.data !== 'object'
    ) {
      throw new HttpError(502, 'Layanan AI mengembalikan respons tidak valid.');
    }
    return json.data;
  } catch (error) {
    const timedOut = signal.aborted
      || (error instanceof Error && ['TimeoutError', 'AbortError'].includes(error.name));
    logger.warn(
      { status, elapsed: Date.now() - started, outcome: timedOut ? 'timeout' : outcome },
      'AI proxy request failed',
    );
    if (timedOut) {
      throw new HttpError(504, 'Layanan AI melewati batas waktu. Silakan coba lagi.');
    }
    if (error instanceof HttpError) throw error;
    throw new HttpError(
      502,
      outcome === 'invalid-response'
        ? 'Layanan AI mengembalikan respons tidak valid.'
        : 'Layanan AI tidak dapat dihubungi. Silakan coba lagi.',
    );
  }
}
