'use client';

import { useRouter } from 'next/navigation';
import type React from 'react';
import { useEffect, useState } from 'react';

import { Button } from '@/components/ui/button';
import { Field } from '@/components/ui/field';
import { LoadingSpinner } from '@/components/ui/loading-spinner';
import { JAM_OPTIONS, SESSION_KEYS } from '@/lib/constants';
import { formatRupiah, getTomorrowInputValue, isPastTimeForDate } from '@/lib/format';
import { type TienReservation, readSession, writeSession } from '@/lib/session';
import { useAuth } from '@/lib/use-auth';
import { cn } from '@/lib/utils';
import type { Service } from '@rag-salon/shared-types';

type FormState = {
  phone: string;
  serviceIds: number[];
  date: string;
  time: string;
  notes: string;
};

const initialState: FormState = {
  phone: '',
  serviceIds: [],
  date: '',
  time: '',
  notes: '',
};

export function ReservationForm() {
  const router = useRouter();
  const { user } = useAuth();
  const [services, setServices] = useState<Service[]>([]);
  const [isLoadingCatalog, setIsLoadingCatalog] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');
  const [form, setForm] = useState<FormState>(initialState);
  const [errors, setErrors] = useState<Partial<Record<keyof FormState, string>>>({});

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const res = await fetch('/api/services', { cache: 'no-store' });
        if (active && res.ok) {
          const body = (await res.json()) as { data: Service[] };
          setServices(body.data);
        }
      } finally {
        if (active) setIsLoadingCatalog(false);
      }
    }
    load();

    const reservation = readSession<TienReservation>(SESSION_KEYS.reservation);
    if (reservation) {
      setForm({
        phone: reservation.phone,
        serviceIds: reservation.items.map((item) => item.serviceId),
        date: reservation.date,
        time: reservation.time,
        notes: reservation.notes ?? '',
      });
    } else {
      setForm((current) => ({
        ...current,
        date: getTomorrowInputValue(),
      }));
    }

    return () => {
      active = false;
    };
  }, []);

  const selectedServices = services.filter((service) => form.serviceIds.includes(service.id));
  const totalPrice = selectedServices.reduce((sum, service) => sum + service.price, 0);

  const toggleService = (id: number) => {
    setForm((current) => ({
      ...current,
      serviceIds: current.serviceIds.includes(id)
        ? current.serviceIds.filter((item) => item !== id)
        : [...current.serviceIds, id],
    }));
    setErrors((current) => ({ ...current, serviceIds: undefined }));
  };

  const updateField = (field: keyof FormState, value: string) => {
    setForm((current) => ({ ...current, [field]: value }));
    setErrors((current) => ({ ...current, [field]: undefined }));
  };

  const validate = () => {
    const nextErrors: Partial<Record<keyof FormState, string>> = {};

    if (!form.phone.trim()) nextErrors.phone = 'Nomor telepon wajib diisi.';
    if (form.phone.replace(/\D/g, '').length < 10)
      nextErrors.phone = 'Nomor telepon minimal 10 digit.';
    if (form.serviceIds.length === 0) nextErrors.serviceIds = 'Pilih minimal satu layanan.';
    if (!form.date) nextErrors.date = 'Tanggal reservasi wajib diisi.';
    if (!form.time) nextErrors.time = 'Jam reservasi wajib diisi.';
    if (form.notes.length > 500) nextErrors.notes = 'Catatan maksimal 500 karakter.';

    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitError('');

    if (!validate()) {
      return;
    }

    setIsSubmitting(true);
    try {
      const res = await fetch('/api/reservations', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          serviceIds: form.serviceIds,
          date: form.date,
          time: form.time,
          notes: form.notes || undefined,
        }),
      });
      const body = (await res.json().catch(() => null)) as {
        data?: TienReservation;
        detail?: string;
        title?: string;
      } | null;

      if (!res.ok || !body?.data) {
        if (res.status === 401) {
          router.push('/auth');
          return;
        }
        setSubmitError(body?.detail ?? body?.title ?? 'Gagal membuat reservasi.');
        return;
      }

      const reservation = body.data;
      writeSession(SESSION_KEYS.reservation, {
        ...reservation,
        customerName: user?.name ?? '',
        email: user?.email ?? '',
        phone: form.phone,
      });
      router.push('/reservation/summary');
    } catch {
      setSubmitError('Terjadi kesalahan jaringan. Silakan coba lagi.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoadingCatalog) {
    return <LoadingSpinner label="Memuat katalog layanan..." />;
  }

  return (
    <form className="form-card reservation-form" onSubmit={handleSubmit}>
      <Field label="Nomor Telepon" htmlFor="phone" error={errors.phone}>
        <input
          id="phone"
          type="tel"
          value={form.phone}
          onChange={(event) => updateField('phone', event.target.value)}
          required
        />
      </Field>
      <Field
        label="Pilihan Layanan"
        htmlFor="serviceIds"
        hint="Boleh pilih lebih dari satu"
        error={errors.serviceIds}
      >
        <div className="service-check-list">
          {services.map((service) => {
            const active = form.serviceIds.includes(service.id);
            return (
              <button
                key={service.id}
                type="button"
                className={cn('service-check-item', active && 'service-check-item--active')}
                onClick={() => toggleService(service.id)}
                aria-pressed={active}
              >
                <span className="service-check-item__name">{service.name}</span>
                <span className="service-check-item__meta">
                  {service.durationMin} menit • {formatRupiah(service.price)}
                </span>
              </button>
            );
          })}
        </div>
      </Field>
      <div className="form-grid form-grid--2">
        <Field label="Tanggal Reservasi" htmlFor="date" error={errors.date}>
          <input
            id="date"
            type="date"
            min={getTomorrowInputValue()}
            value={form.date}
            onChange={(event) => updateField('date', event.target.value)}
            required
          />
        </Field>
        <Field label="Jam Reservasi" htmlFor="time" error={errors.time}>
          <select
            id="time"
            value={form.time}
            onChange={(event) => updateField('time', event.target.value)}
            required
          >
            <option value="">Pilih jam</option>
            {JAM_OPTIONS.map((time) => (
              <option key={time} value={time} disabled={isPastTimeForDate(form.date, time)}>
                {time}
              </option>
            ))}
          </select>
        </Field>
      </div>
      <Field
        label="Catatan Tambahan"
        htmlFor="notes"
        hint={`${form.notes.length}/500 karakter`}
        error={errors.notes}
      >
        <textarea
          id="notes"
          rows={4}
          value={form.notes}
          onChange={(event) => updateField('notes', event.target.value)}
          maxLength={500}
        />
      </Field>
      <aside className="reservation-preview">
        <h2>Preview Reservasi</h2>
        {selectedServices.length > 0 ? (
          <>
            <ul className="reservation-preview__list">
              {selectedServices.map((service) => (
                <li key={service.id}>
                  <span>{service.name}</span>
                  <span>{formatRupiah(service.price)}</span>
                </li>
              ))}
            </ul>
            <span>Total</span>
            <strong>{formatRupiah(totalPrice)}</strong>
          </>
        ) : (
          <p className="muted-text">Pilih layanan untuk melihat total harga.</p>
        )}
      </aside>
      {submitError ? <p className="text-red-500 text-sm font-semibold">{submitError}</p> : null}
      <Button type="submit" size="lg" disabled={isSubmitting}>
        {isSubmitting ? 'Menyimpan...' : 'Simpan dan Lihat Ringkasan'}
      </Button>
    </form>
  );
}
