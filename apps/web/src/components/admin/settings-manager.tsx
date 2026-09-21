'use client';

import { Save } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';

import { Button } from '@/components/ui/button';
import { LoadingSpinner } from '@/components/ui/loading-spinner';
import { Tag } from '@/components/ui/tag';
import { adminApi } from '@/lib/admin-api';

interface SiteInfo {
  name: string;
  tagline: string;
  address: string;
  phone: string;
  email: string;
  mapEmbedUrl: string;
  operatingHours: Array<{ days: string; hours: string }>;
  socialLinks: Array<{ platform: string; url: string; icon: string }>;
  stats: Array<{ label: string; value: string }>;
}

const EMPTY_SITE: SiteInfo = {
  name: '',
  tagline: '',
  address: '',
  phone: '',
  email: '',
  mapEmbedUrl: '',
  operatingHours: [],
  socialLinks: [],
  stats: [],
};

export function SettingsManager() {
  const [site, setSite] = useState<SiteInfo>(EMPTY_SITE);
  const [geminiMasked, setGeminiMasked] = useState('');
  const [geminiInput, setGeminiInput] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [note, setNote] = useState('');

  const load = useCallback(async () => {
    try {
      const rows = await adminApi.list<{ key: string; value: unknown }>('settings');
      const siteRow = rows.find((r) => r.key === 'site');
      if (siteRow?.value) setSite({ ...EMPTY_SITE, ...(siteRow.value as SiteInfo) });
      const gem = rows.find((r) => r.key === 'gemini_api_key');
      setGeminiMasked(typeof gem?.value === 'string' ? gem.value : '');
      setError('');
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const save = async () => {
    setSaving(true);
    setError('');
    try {
      const entries: Array<{ key: string; value: unknown }> = [{ key: 'site', value: site }];
      if (geminiInput.trim()) {
        entries.push({ key: 'gemini_api_key', value: geminiInput.trim() });
      }
      const res = await fetch('/api/admin/settings', {
        method: 'PUT',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ entries }),
      });
      if (!res.ok) {
        const b = (await res.json().catch(() => null)) as { detail?: string; title?: string } | null;
        throw new Error(b?.detail ?? b?.title ?? 'Gagal menyimpan.');
      }
      setGeminiInput('');
      setNote('Pengaturan disimpan.');
      setTimeout(() => setNote(''), 2500);
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <LoadingSpinner label="Memuat pengaturan..." />;

  return (
    <section className="admin-panel">
      <div className="admin-panel__toolbar">
        <h1>Pengaturan</h1>
        <div className="admin-panel__toolbar-actions">
          {note ? <span className="admin-perm-saved">{note}</span> : null}
          <Button size="sm" onClick={() => void save()} disabled={saving}>
            <Save size={16} /> {saving ? 'Menyimpan...' : 'Simpan'}
          </Button>
        </div>
      </div>
      {error ? <p className="text-red-500 text-sm font-semibold">{error}</p> : null}

      <h2 className="admin-panel__section-title">Info Salon (Landing)</h2>
      <div className="admin-form">
        <label className="admin-form__field">
          <span>Nama Salon</span>
          <input type="text" value={site.name} onChange={(e) => setSite({ ...site, name: e.target.value })} />
        </label>
        <label className="admin-form__field">
          <span>Tagline</span>
          <input
            type="text"
            value={site.tagline}
            onChange={(e) => setSite({ ...site, tagline: e.target.value })}
          />
        </label>
        <label className="admin-form__field">
          <span>Telepon</span>
          <input type="text" value={site.phone} onChange={(e) => setSite({ ...site, phone: e.target.value })} />
        </label>
        <label className="admin-form__field">
          <span>Email</span>
          <input type="email" value={site.email} onChange={(e) => setSite({ ...site, email: e.target.value })} />
        </label>
        <label className="admin-form__field admin-form__field--full">
          <span>Alamat</span>
          <input
            type="text"
            value={site.address}
            onChange={(e) => setSite({ ...site, address: e.target.value })}
          />
        </label>
        <label className="admin-form__field admin-form__field--full">
          <span>Google Maps Embed URL</span>
          <input
            type="text"
            value={site.mapEmbedUrl}
            onChange={(e) => setSite({ ...site, mapEmbedUrl: e.target.value })}
          />
        </label>
      </div>

      <h2 className="admin-panel__section-title">Gemini API Key</h2>
      <div className="admin-form">
        <label className="admin-form__field admin-form__field--full">
          <span>
            API Key (saat ini: {geminiMasked ? <Tag tone="green">{geminiMasked}</Tag> : <Tag tone="red">belum diset</Tag>})
          </span>
          <input
            type="password"
            value={geminiInput}
            onChange={(e) => setGeminiInput(e.target.value)}
            placeholder="Isi untuk mengganti (kosongkan bila tidak diubah)"
          />
        </label>
      </div>
      <p className="muted-text">
        Key disimpan di database. Brain engine (apps/ai) membacanya otomatis untuk embedding &amp; LLM.
      </p>
    </section>
  );
}
