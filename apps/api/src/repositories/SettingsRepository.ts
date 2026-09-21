import { BaseRepository } from './BaseRepository';

export interface SettingRow {
  id: number;
  key: string;
  value: unknown;
  created_at: string;
  updated_at: string;
}

export class SettingsRepository extends BaseRepository {
  list(): Promise<SettingRow[]> {
    return this.db<SettingRow>('site_settings').orderBy('key');
  }

  async get(key: string): Promise<unknown> {
    const row = await this.db<SettingRow>('site_settings').where({ key }).first();
    return row?.value ?? null;
  }

  async upsert(key: string, value: unknown): Promise<void> {
    const encoded = JSON.stringify(value ?? null);
    await this.db('site_settings')
      .insert({ key, value: encoded })
      .onConflict('key')
      .merge({ value: encoded, updated_at: this.db.fn.now() });
  }
}

export const settingsRepository = new SettingsRepository();
