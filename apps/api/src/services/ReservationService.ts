import type { CreateReservationRequest, Reservation } from '@rag-salon/shared-types';
import {
  type ReservationWithItems,
  reservationRepository,
} from '../repositories/ReservationRepository';
import { serviceRepository } from '../repositories/ServiceRepository';
import { HttpError } from '../utils/problemDetails';

interface AuthLike {
  userId: number;
  permissions: string[];
  type: number;
}

function canAccessAll(auth: AuthLike): boolean {
  return auth.type === 0 || auth.permissions.includes('reservations.read');
}

function assertCanAccess(auth: AuthLike, userId: number): void {
  if (!canAccessAll(auth) && userId !== auth.userId) {
    throw new HttpError(403, 'Anda tidak memiliki izin untuk aksi ini');
  }
}

function mapReservation(withItems: ReservationWithItems): Reservation {
  return {
    id: withItems.reservation.code,
    userId: withItems.reservation.user_id,
    items: withItems.items.map((item) => ({
      serviceId: item.service_id,
      serviceName: item.service_name,
      price: item.price,
    })),
    total: withItems.reservation.total,
    date: withItems.reservation.date,
    time: withItems.reservation.time,
    notes: withItems.reservation.notes ?? undefined,
    status: withItems.reservation.status as Reservation['status'],
    createdAt: withItems.reservation.created_at,
  };
}

export class ReservationService {
  async create(userId: number, input: CreateReservationRequest): Promise<Reservation> {
    const services = await serviceRepository.findByIds(input.serviceIds);
    if (services.length !== input.serviceIds.length) {
      throw new HttpError(400, 'Satu atau lebih layanan tidak tersedia');
    }

    const total = services.reduce((sum, s) => sum + s.price, 0);
    const code = await reservationRepository.nextInvoiceCode(input.date);

    const created = await reservationRepository.create({
      code,
      user_id: userId,
      date: input.date,
      time: input.time,
      notes: input.notes,
      total,
      items: services.map((s) => ({ service_id: s.id, service_name: s.name, price: s.price })),
    });

    return mapReservation(created);
  }

  async list(auth: AuthLike): Promise<Reservation[]> {
    const rows = canAccessAll(auth)
      ? await reservationRepository.listAll()
      : await reservationRepository.listByUser(auth.userId);
    const result: Reservation[] = [];
    for (const row of rows) {
      const withItems = await reservationRepository.findById(row.id);
      if (withItems) result.push(mapReservation(withItems));
    }
    return result;
  }

  async byReservationId(auth: AuthLike, id: number): Promise<Reservation> {
    const withItems = await reservationRepository.findById(id);
    if (!withItems) {
      throw new HttpError(404, 'Reservasi tidak ditemukan');
    }
    assertCanAccess(auth, withItems.reservation.user_id);
    return mapReservation(withItems);
  }

  async byCode(auth: AuthLike, code: string): Promise<Reservation> {
    const row = await reservationRepository.findByCode(code);
    if (!row) {
      throw new HttpError(404, 'Reservasi tidak ditemukan');
    }
    assertCanAccess(auth, row.user_id);
    const withItems = await reservationRepository.findById(row.id);
    if (!withItems) throw new HttpError(404, 'Reservasi tidak ditemukan');
    return mapReservation(withItems);
  }

  async cancel(auth: AuthLike, code: string): Promise<Reservation> {
    const row = await reservationRepository.findByCode(code);
    if (!row) {
      throw new HttpError(404, 'Reservasi tidak ditemukan');
    }
    assertCanAccess(auth, row.user_id);
    if (row.status === 'cancelled') {
      throw new HttpError(409, 'Reservasi sudah dibatalkan');
    }
    const updated = await reservationRepository.updateStatus(row.id, 'cancelled');
    if (!updated) throw new HttpError(404, 'Reservasi tidak ditemukan');
    const items = (await reservationRepository.findById(row.id))?.items ?? [];
    return mapReservation({ reservation: updated, items });
  }
}

export const reservationService = new ReservationService();
