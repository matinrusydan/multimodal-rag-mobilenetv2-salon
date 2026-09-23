import { settingsRepository } from '../repositories/SettingsRepository';

const GEMINI_KEY = 'gemini_api_key';
const MASK = '••••••••';

function maskKey(value: unknown): unknown {
  if (typeof value !== 'string' || value.length === 0) return '';
  return `${value.slice(0, 4)}${MASK}${value.slice(-4)}`;
}

export class SettingsService {
  /** Semua settings untuk admin (gemini_api_key di-mask). */
  async listForAdmin(): Promise<Array<{ key: string; value: unknown }>> {
    const rows = await settingsRepository.list();
    return rows.map((r) => ({
      key: r.key,
      value: r.key === GEMINI_KEY ? maskKey(r.value) : r.value,
    }));
  }

  /** Hanya setting publik (untuk landing): site_info. */
  async publicSettings(): Promise<Record<string, unknown>> {
    return {
      site: (await settingsRepository.get('site')) ?? null,
    };
  }

  /** Nilai mentah gemini key (untuk dipakai apps/ai). */
  async geminiKey(): Promise<string | null> {
    const v = await settingsRepository.get(GEMINI_KEY);
    return typeof v === 'string' && v.length > 0 ? v : null;
  }

  /** Nilai mentah setting apapun (internal / apps/ai). */
  async rawGet(key: string): Promise<unknown> {
    return settingsRepository.get(key);
  }

  async update(entries: Array<{ key: string; value: unknown }>): Promise<void> {
    for (const e of entries) {
      // Jangan timpa key bila nilainya masih masked (tidak diubah).
      if (e.key === GEMINI_KEY && typeof e.value === 'string' && e.value.includes(MASK)) {
        continue;
      }
      await settingsRepository.upsert(e.key, e.value);
    }
  }
}

export const settingsService = new SettingsService();
