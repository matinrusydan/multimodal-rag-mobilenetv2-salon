'use client';

import { useRouter } from 'next/navigation';
import type React from 'react';
import { useEffect, useMemo, useState } from 'react';

import { Button } from '@/components/ui/button';
import { Field } from '@/components/ui/field';
import { PriceDisplay } from '@/components/ui/price-display';
import { getServiceById, services } from '@/data/services';
import { JAM_OPTIONS, SESSION_KEYS } from '@/lib/constants';
import { formatRupiah, getTomorrowInputValue, isPastTimeForDate } from '@/lib/format';
import { type TienAuth, type TienReservation, readSession, writeSession } from '@/lib/session';
import { generateInvoiceNumber } from '@/lib/utils';

type FormState = {
  customerName: string;
  email: string;
  phone: string;
  serviceId: string;
  date: string;
  time: string;
  notes: string;
};

const initialState: FormState = {
  customerName: '',
  email: '',
  phone: '',
  serviceId: '',
  date: '',
  time: '',
  notes: '',
};

export function ReservationForm() {
  const router = useRouter();
  const [form, setForm] = useState<FormState>(initialState);
  const [errors, setErrors] = useState<Partial<Record<keyof FormState, string>>>({});

  useEffect(() => {
    const auth = readSession<TienAuth>(SESSION_KEYS.auth);
    const reservation = readSession<TienReservation>(SESSION_KEYS.reservation);

    if (reservation) {
      setForm({
        customerName: reservation.customerName,
        email: reservation.email,
        phone: reservation.phone,
        serviceId: reservation.serviceId,
        date: reservation.date,
        time: reservation.time,
        notes: reservation.notes,
      });
      return;
    }

    setForm((current) => ({
      ...current,
      customerName: auth?.user.name ?? '',
      email: auth?.user.email ?? '',
      date: getTomorrowInputValue(),
    }));
  }, []);

  const selectedService = useMemo(() => getServiceById(form.serviceId), [form.serviceId]);
  const totalPrice = selectedService?.discountPrice ?? selectedService?.price ?? 0;

  const updateField = (field: keyof FormState, value: string) => {
    setForm((current) => ({ ...current, [field]: value }));
    setErrors((current) => ({ ...current, [field]: undefined }));
  };

  const validate = () => {
    const nextErrors: Partial<Record<keyof FormState, string>> = {};

    if (!form.customerName.trim()) nextErrors.customerName = 'Nama lengkap wajib diisi.';
    if (!form.email.trim()) nextErrors.email = 'Email wajib diisi.';
    if (!form.phone.trim()) nextErrors.phone = 'Nomor telepon wajib diisi.';
    if (form.phone.replace(/\D/g, '').length < 10)
      nextErrors.phone = 'Nomor telepon minimal 10 digit.';
    if (!form.serviceId) nextErrors.serviceId = 'Pilih layanan terlebih dahulu.';
    if (!form.date) nextErrors.date = 'Tanggal reservasi wajib diisi.';
    if (!form.time) nextErrors.time = 'Jam reservasi wajib diisi.';
    if (form.notes.length > 500) nextErrors.notes = 'Catatan maksimal 500 karakter.';

    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!validate() || !selectedService) {
      return;
    }

    writeSession(SESSION_KEYS.reservation, {
      customerName: form.customerName,
      email: form.email,
      phone: form.phone,
      serviceId: selectedService.id,
      serviceName: selectedService.name,
      servicePrice: totalPrice,
      serviceDurationMinutes: selectedService.durationMinutes,
      date: form.date,
      time: form.time,
      notes: form.notes,
      invoiceNumber: generateInvoiceNumber(),
    });

    router.push('/reservation/summary');
  };

  return (
    <form className="form-card reservation-form" onSubmit={handleSubmit}>
      <div className="form-grid form-grid--2">
        <Field label="Nama Lengkap" htmlFor="customerName" error={errors.customerName}>
          <input
            id="customerName"
            value={form.customerName}
            onChange={(event) => updateField('customerName', event.target.value)}
            required
          />
        </Field>
        <Field label="Email" htmlFor="email" error={errors.email}>
          <input
            id="email"
            type="email"
            value={form.email}
            onChange={(event) => updateField('email', event.target.value)}
            required
          />
        </Field>
      </div>
      <Field label="Nomor Telepon" htmlFor="phone" error={errors.phone}>
        <input
          id="phone"
          type="tel"
          value={form.phone}
          onChange={(event) => updateField('phone', event.target.value)}
          required
        />
      </Field>
      <Field label="Pilihan Layanan" htmlFor="serviceId" error={errors.serviceId}>
        <select
          id="serviceId"
          value={form.serviceId}
          onChange={(event) => updateField('serviceId', event.target.value)}
          required
        >
          <option value="">Pilih layanan</option>
          {services.map((service) => (
            <option key={service.id} value={service.id}>
              {service.name} - {formatRupiah(service.discountPrice ?? service.price)}
            </option>
          ))}
        </select>
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
        {selectedService ? (
          <>
            <p>{selectedService.name}</p>
            <span>{selectedService.durationMinutes} menit</span>
            <PriceDisplay
              price={selectedService.price}
              discountPrice={selectedService.discountPrice}
            />
          </>
        ) : (
          <p className="muted-text">Pilih layanan untuk melihat total harga.</p>
        )}
      </aside>
      <Button type="submit" size="lg">
        Simpan dan Lihat Ringkasan
      </Button>
    </form>
  );
}
