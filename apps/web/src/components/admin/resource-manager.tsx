'use client';

import type React from 'react';
import { useCallback, useEffect, useState } from 'react';

import { Button } from '@/components/ui/button';
import { LoadingSpinner } from '@/components/ui/loading-spinner';

export type FieldType =
  | 'text'
  | 'email'
  | 'password'
  | 'number'
  | 'select'
  | 'multiselect'
  | 'textarea';

export interface FieldSpec {
  key: string;
  label: string;
  type: FieldType;
  source?: string;
  required?: boolean;
  minLength?: number;
  placeholder?: string;
  createOnly?: boolean;
  options?: { value: string; label: string }[];
}

export interface Column {
  key: string;
  label: string;
  render?: (row: Record<string, unknown>) => React.ReactNode;
}

export interface AssignSpec {
  suffix: string;
  key: string;
}

export interface ResourceSpec {
  resource: string;
  singular: string;
  columns: Column[];
  fields: FieldSpec[];
  buildCreate(form: Record<string, unknown>): Record<string, unknown>;
  buildUpdate(form: Record<string, unknown>): Record<string, unknown>;
  assign?: AssignSpec;
  optionSources?: { key: string; url: string }[];
}

function escapeValue(value: unknown): string {
  if (value === null || value === undefined) return '-';
  if (Array.isArray(value)) {
    return value
      .map((item) => {
        if (typeof item === 'object' && item !== null) {
          const record = item as Record<string, unknown>;
          return String(record.code ?? record.name ?? '');
        }
        return String(item);
      })
      .filter(Boolean)
      .join(', ');
  }
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

function defaultRender(key: string) {
  return (row: Record<string, unknown>) => escapeValue(row[key]);
}

function makeInitialForm(spec: ResourceSpec): Record<string, unknown> {
  const form: Record<string, unknown> = {};
  for (const field of spec.fields) {
    form[field.key] = field.type === 'multiselect' ? [] : '';
  }
  return form;
}

export function ResourceManager({ spec }: { spec: ResourceSpec }) {
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<Record<string, unknown>>(makeInitialForm(spec));
  const [saving, setSaving] = useState(false);
  const [optionMaps, setOptionMaps] = useState<Record<string, { value: string; label: string }[]>>(
    {},
  );

  const fetchList = useCallback(async () => {
    try {
      const res = await fetch(`/api/admin/${spec.resource}`, { cache: 'no-store' });
      const body = (await res.json().catch(() => null)) as {
        data?: Record<string, unknown>[];
        detail?: string;
        title?: string;
      } | null;
      if (!res.ok) {
        setError(body?.detail ?? body?.title ?? 'Gagal memuat data.');
        return;
      }
      setRows(body?.data ?? []);
      setError('');
    } catch {
      setError('Terjadi kesalahan jaringan.');
    } finally {
      setLoading(false);
    }
  }, [spec.resource]);

  useEffect(() => {
    void fetchList();
    if (spec.optionSources) {
      for (const source of spec.optionSources) {
        void fetch(source.url, { cache: 'no-store' })
          .then((res) => res.json())
          .then((body) => {
            const list = (body as { data?: Record<string, unknown>[] }).data ?? [];
            setOptionMaps((current) => ({
              ...current,
              [source.key]: list.map((item) => ({
                value: String(item.id),
                label: String(item.name ?? item.code ?? item.id),
              })),
            }));
          })
          .catch(() => undefined);
      }
    }
  }, [fetchList, spec.optionSources]);

  const setField = (key: string, value: unknown) => {
    setForm((current) => ({ ...current, [key]: value }));
  };

  const resetForm = () => {
    setForm(makeInitialForm(spec));
    setEditingId(null);
  };

  const startEdit = (row: Record<string, unknown>) => {
    const next: Record<string, unknown> = {};
    for (const field of spec.fields) {
      next[field.key] = field.type === 'multiselect' ? [] : (row[field.key] ?? '');
    }
    setForm(next);
    setEditingId(String(row.id));
  };

  const handleSave = async () => {
    setError('');
    setSaving(true);
    try {
      const isEdit = editingId !== null;
      const body = isEdit ? spec.buildUpdate(form) : spec.buildCreate(form);
      const url = `/api/admin/${spec.resource}${isEdit ? `/${editingId}` : ''}`;
      const res = await fetch(url, {
        method: isEdit ? 'PUT' : 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify(body),
      });
      const result = (await res.json().catch(() => null)) as {
        data?: Record<string, unknown>;
        detail?: string;
        title?: string;
      } | null;

      if (!res.ok) {
        setError(result?.detail ?? result?.title ?? 'Gagal menyimpan data.');
        return;
      }

      const targetId =
        editingId ?? (result?.data?.id !== undefined ? String(result.data.id) : null);
      if (spec.assign && targetId && (form[spec.assign.key] as unknown[]).length > 0) {
        await fetch(`/api/admin/${spec.resource}/${targetId}/${spec.assign.suffix}`, {
          method: 'PUT',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({ [spec.assign.key]: form[spec.assign.key] }),
        });
      }

      resetForm();
      await fetchList();
    } catch {
      setError('Terjadi kesalahan jaringan.');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm('Yakin ingin menghapus data ini?')) {
      return;
    }
    setError('');
    try {
      const res = await fetch(`/api/admin/${spec.resource}/${id}`, { method: 'DELETE' });
      if (!res.ok) {
        const body = (await res.json().catch(() => null)) as { detail?: string; title?: string };
        setError(body?.detail ?? body?.title ?? 'Gagal menghapus data.');
        return;
      }
      await fetchList();
    } catch {
      setError('Terjadi kesalahan jaringan.');
    }
  };

  if (loading) {
    return <LoadingSpinner label="Memuat data..." />;
  }

  const optionsFor = (field: FieldSpec) => field.options ?? optionMaps[field.source ?? ''] ?? [];

  return (
    <section className="admin-panel">
      <div className="admin-panel__toolbar">
        <h1>{editingId === null ? `Tambah ${spec.singular}` : `Edit ${spec.singular}`}</h1>
        {editingId !== null ? (
          <Button variant="outline" size="sm" onClick={resetForm}>
            Batal Edit
          </Button>
        ) : null}
      </div>
      <div className="admin-panel__form">
        {spec.fields.map((field) => {
          if (field.type === 'multiselect') {
            const options = optionsFor(field);
            const values = (form[field.key] as string[] | number[]) ?? [];
            const strings = values.map(String);
            return (
              <div key={field.key} className="admin-field">
                <span>{field.label}</span>
                <div className="admin-field__checks">
                  {options.map((option) => {
                    const active = strings.includes(option.value);
                    return (
                      <label key={option.value} className="admin-check">
                        <input
                          type="checkbox"
                          checked={active}
                          onChange={() => {
                            const next = active
                              ? strings.filter((item) => item !== option.value)
                              : [...strings, option.value];
                            setField(
                              field.key,
                              next.map((item) => (/^\d+$/.test(item) ? Number(item) : item)),
                            );
                          }}
                        />
                        {option.label}
                      </label>
                    );
                  })}
                </div>
              </div>
            );
          }
          return (
            <label key={field.key} className="admin-field" htmlFor={`admin-${field.key}`}>
              <span>{field.label}</span>
              {field.type === 'select' ? (
                <select
                  id={`admin-${field.key}`}
                  value={String(form[field.key] ?? '')}
                  onChange={(event) => setField(field.key, event.target.value)}
                >
                  <option value="">Pilih...</option>
                  {optionsFor(field).map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  id={`admin-${field.key}`}
                  type={
                    field.type === 'password'
                      ? 'password'
                      : field.type === 'number'
                        ? 'number'
                        : field.type
                  }
                  value={String(form[field.key] ?? '')}
                  required={field.required && (editingId === null || !field.createOnly)}
                  minLength={field.minLength}
                  placeholder={field.placeholder}
                  onChange={(event) =>
                    setField(
                      field.key,
                      field.type === 'number' ? Number(event.target.value) : event.target.value,
                    )
                  }
                />
              )}
            </label>
          );
        })}
        {error ? <p className="text-red-500 text-sm font-semibold">{error}</p> : null}
        <div className="admin-panel__actions">
          <Button size="sm" onClick={handleSave} disabled={saving}>
            {saving ? 'Menyimpan...' : 'Simpan'}
          </Button>
        </div>
      </div>
      <div className="admin-table">
        <table>
          <thead>
            <tr>
              {spec.columns.map((column) => (
                <th key={column.key}>{column.label}</th>
              ))}
              <th>Aksi</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={String(row.id)}>
                {spec.columns.map((column) => (
                  <td key={column.key}>{(column.render ?? defaultRender(column.key))(row)}</td>
                ))}
                <td>
                  <div className="admin-table__actions">
                    <Button variant="outline" size="sm" onClick={() => startEdit(row)}>
                      Edit
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => handleDelete(String(row.id))}>
                      Hapus
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
            {rows.length === 0 ? (
              <tr>
                <td colSpan={spec.columns.length + 1} className="admin-table__empty">
                  Belum ada data {spec.singular}.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </section>
  );
}
