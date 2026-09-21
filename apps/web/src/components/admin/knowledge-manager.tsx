'use client';

import { FileText, Plus, RefreshCw, Save, Trash2 } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';

import { Button } from '@/components/ui/button';
import { MarkdownLite } from '@/components/consult/markdown-lite';
import { LoadingSpinner } from '@/components/ui/loading-spinner';
import { Modal } from '@/components/ui/modal';

interface DocItem {
  name: string;
  size: number;
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api/admin/knowledge${path}`, {
    cache: 'no-store',
    ...init,
    headers: {
      ...(init?.body ? { 'content-type': 'application/json' } : {}),
      ...(init?.headers ?? {}),
    },
  });
  const body = (await res.json().catch(() => null)) as { data?: T; detail?: string; title?: string } | null;
  if (!res.ok) throw new Error(body?.detail ?? body?.title ?? 'Terjadi kesalahan.');
  return body?.data as T;
}

export function KnowledgeManager() {
  const [docs, setDocs] = useState<DocItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [note, setNote] = useState('');

  const [activeName, setActiveName] = useState<string | null>(null);
  const [content, setContent] = useState('');
  const [saving, setSaving] = useState(false);
  const [preview, setPreview] = useState(false);

  const [createOpen, setCreateOpen] = useState(false);
  const [newName, setNewName] = useState('');

  const loadList = useCallback(async () => {
    try {
      setDocs(await req<DocItem[]>('/'));
      setError('');
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadList();
  }, [loadList]);

  const openDoc = async (name: string) => {
    setError('');
    try {
      const d = await req<{ name: string; content: string }>(`/${encodeURIComponent(name)}`);
      setActiveName(d.name);
      setContent(d.content);
      setPreview(false);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const saveDoc = async () => {
    if (!activeName) return;
    setSaving(true);
    setError('');
    try {
      await req(`/${encodeURIComponent(activeName)}`, {
        method: 'PUT',
        body: JSON.stringify({ content }),
      });
      // re-ingest otomatis
      await req('/reingest', { method: 'POST' });
      setNote('Disimpan & re-index ke ChromaDB.');
      setTimeout(() => setNote(''), 3000);
      await loadList();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const reindex = async () => {
    setSaving(true);
    setError('');
    try {
      await req('/reingest', { method: 'POST' });
      setNote('Re-index selesai.');
      setTimeout(() => setNote(''), 2500);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const createDoc = async () => {
    const name = newName.trim();
    if (!name) return;
    const fileName = name.endsWith('.md') ? name : `${name}.md`;
    try {
      await req(`/${encodeURIComponent(fileName)}`, {
        method: 'PUT',
        body: JSON.stringify({ content: `# ${name.replace(/\.md$/, '')}\n\n` }),
      });
      setCreateOpen(false);
      setNewName('');
      await loadList();
      await openDoc(fileName);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const deleteDoc = async (name: string) => {
    if (!window.confirm(`Hapus file ${name}?`)) return;
    try {
      await req(`/${encodeURIComponent(name)}`, { method: 'DELETE' });
      if (activeName === name) {
        setActiveName(null);
        setContent('');
      }
      await loadList();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  if (loading) return <LoadingSpinner label="Memuat dokumen..." />;

  return (
    <section className="admin-panel">
      <div className="admin-panel__toolbar">
        <h1>Dokumen RAG (.md)</h1>
        <div className="admin-panel__toolbar-actions">
          {note ? <span className="admin-perm-saved">{note}</span> : null}
          <Button variant="outline" size="sm" onClick={() => void reindex()} disabled={saving}>
            <RefreshCw size={16} /> Re-index
          </Button>
          <Button size="sm" onClick={() => setCreateOpen(true)}>
            <Plus size={16} /> Dokumen Baru
          </Button>
        </div>
      </div>
      {error ? <p className="text-red-500 text-sm font-semibold">{error}</p> : null}

      <div className="admin-kb">
        <aside className="admin-kb__list">
          {docs.map((d) => (
            <div
              key={d.name}
              role="button"
              tabIndex={0}
              className={
                d.name === activeName ? 'admin-kb__item admin-kb__item--active' : 'admin-kb__item'
              }
              onClick={() => void openDoc(d.name)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') void openDoc(d.name);
              }}
            >
              <FileText size={15} />
              <span>{d.name}</span>
              <button
                type="button"
                className="admin-kb__del"
                aria-label="Hapus"
                onClick={(e) => {
                  e.stopPropagation();
                  void deleteDoc(d.name);
                }}
              >
                <Trash2 size={13} />
              </button>
            </div>
          ))}
          {docs.length === 0 ? <p className="muted-text">Belum ada dokumen.</p> : null}
        </aside>

        <div className="admin-kb__editor">
          {activeName ? (
            <>
              <div className="admin-kb__editor-head">
                <code>{activeName}</code>
                <div className="admin-panel__toolbar-actions">
                  <Button variant="outline" size="sm" onClick={() => setPreview((p) => !p)}>
                    {preview ? 'Edit' : 'Preview'}
                  </Button>
                  <Button size="sm" onClick={() => void saveDoc()} disabled={saving}>
                    <Save size={16} /> {saving ? 'Menyimpan...' : 'Simpan & Re-index'}
                  </Button>
                </div>
              </div>
              {preview ? (
                <div className="admin-kb__preview">
                  <MarkdownLite content={content} />
                </div>
              ) : (
                <textarea
                  className="admin-kb__textarea"
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  spellCheck={false}
                />
              )}
            </>
          ) : (
            <p className="muted-text">Pilih dokumen di kiri untuk mengedit, atau buat dokumen baru.</p>
          )}
        </div>
      </div>

      <Modal
        open={createOpen}
        onOpenChange={setCreateOpen}
        title="Dokumen Baru"
        footer={
          <>
            <Button variant="outline" size="sm" onClick={() => setCreateOpen(false)}>
              Batal
            </Button>
            <Button size="sm" onClick={() => void createDoc()}>
              Buat
            </Button>
          </>
        }
      >
        <div className="admin-form">
          <label className="admin-form__field admin-form__field--full">
            <span>Nama file (tanpa/ dengan .md)</span>
            <input
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="mis. promo-bulan-ini"
            />
          </label>
        </div>
      </Modal>
    </section>
  );
}
