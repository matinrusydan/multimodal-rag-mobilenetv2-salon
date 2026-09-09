import { generateInvoiceNumber } from '@rag-salon/shared-utils';
import { BaseRepository } from './BaseRepository';

export interface ReservationRow {
  id: number;
  code: string;
  user_id: number;
  date: string;
  time: string;
  notes: string | null;
  status: string;
  total: number;
  expires_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReservationItemRow {
  id: number;
  reservation_id: number;
  service_id: number;
  service_name: string;
  price: number;
}

export interface ReservationWithItems {
  reservation: ReservationRow;
  items: ReservationItemRow[];
}

export class ReservationRepository extends BaseRepository {
  async countByDate(date: string): Promise<number> {
    const row = await this.db('reservations')
      .where('date', date)
      .count<{ count: string }>('*')
      .first();
    return Number(row?.count ?? 0);
  }

  async nextInvoiceCode(date: string): Promise<string> {
    const seq = (await this.countByDate(date)) + 1;
    return generateInvoiceNumber(seq, new Date(`${date}T00:00:00`));
  }

  async create(input: {
    code: string;
    user_id: number;
    date: string;
    time: string;
    notes?: string;
    total: number;
    items: Array<{ service_id: number; service_name: string; price: number }>;
  }): Promise<ReservationWithItems> {
    return this.db.transaction(async (trx) => {
      const [reservation] = await trx<ReservationRow>('reservations')
        .insert({
          code: input.code,
          user_id: input.user_id,
          date: input.date,
          time: input.time,
          notes: input.notes ?? null,
          total: input.total,
          status: 'pending',
          expires_at: new Date(Date.now() + 30 * 60 * 1000).toISOString(),
        })
        .returning('*');

      const items = await trx<ReservationItemRow>('reservation_items')
        .insert(
          input.items.map((item) => ({
            reservation_id: reservation.id,
            service_id: item.service_id,
            service_name: item.service_name,
            price: item.price,
          })),
        )
        .returning('*');

      return { reservation, items };
    });
  }

  async findById(id: number): Promise<ReservationWithItems | undefined> {
    const reservation = await this.db<ReservationRow>('reservations').where({ id }).first();
    if (!reservation) return undefined;
    const items = await this.db<ReservationItemRow>('reservation_items').where({
      reservation_id: id,
    });
    return { reservation, items };
  }

  async findByCode(code: string): Promise<ReservationRow | undefined> {
    return this.db<ReservationRow>('reservations').where({ code }).first();
  }

  async listByUser(userId: number): Promise<ReservationRow[]> {
    return this.db<ReservationRow>('reservations').where({ user_id: userId }).orderBy('id', 'desc');
  }

  listAll(): Promise<ReservationRow[]> {
    return this.db<ReservationRow>('reservations').orderBy('id', 'desc');
  }

  async updateStatus(id: number, status: string): Promise<ReservationRow | undefined> {
    await this.db<ReservationRow>('reservations')
      .where({ id })
      .update({ status, updated_at: this.db.fn.now() });
    return this.db<ReservationRow>('reservations').where({ id }).first();
  }
}

export const reservationRepository = new ReservationRepository();
