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

  /** Statistik reservasi: total, per-status, per-hari (N hari terakhir). */
  async stats(days = 7): Promise<{
    total: number;
    by_status: Array<{ status: string; count: number }>;
    by_day: Array<{ date: string; count: number; total: number }>;
  }> {
    const total = await this.db('reservations').count({ count: '*' }).first();
    const byStatusRows = (await this.db('reservations')
      .groupBy('status')
      .select('status')
      .count({ count: '*' })) as unknown as Array<{ status: string; count: number | string }>;

    const since = new Date();
    since.setDate(since.getDate() - days);
    const sinceStr = since.toISOString().slice(0, 10);
    const byDayRows = (await this.db('reservations')
      .where('date', '>=', sinceStr)
      .groupBy('date')
      .orderBy('date', 'desc')
      .select('date')
      .count({ count: '*' })
      .sum({ total: 'total' })) as unknown as Array<{
      date: string;
      count: number | string;
      total: number | string | null;
    }>;

    return {
      total: Number((total as { count?: string } | undefined)?.count ?? 0),
      by_status: byStatusRows.map((r) => ({
        status: String(r.status),
        count: Number(r.count ?? 0),
      })),
      by_day: byDayRows.map((r) => ({
        date: String(r.date),
        count: Number(r.count ?? 0),
        total: Number(r.total ?? 0),
      })),
    };
  }
}

export const reservationRepository = new ReservationRepository();
