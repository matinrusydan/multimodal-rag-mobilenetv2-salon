import { generatePaymentId } from '@rag-salon/shared-utils';
import { BaseRepository } from './BaseRepository';

export interface PaymentRow {
  id: number;
  code: string;
  reservation_id: number;
  user_id: number;
  method: string;
  status: string;
  amount: number;
  paid_at: string | null;
  created_at: string;
  updated_at: string;
}

export class PaymentRepository extends BaseRepository {
  async findByReservationId(reservationId: number): Promise<PaymentRow | undefined> {
    return this.db<PaymentRow>('payments').where({ reservation_id: reservationId }).first();
  }

  async create(input: {
    reservation_id: number;
    user_id: number;
    method: string;
    amount: number;
  }): Promise<PaymentRow> {
    const code = generatePaymentId();
    const rows = await this.db<PaymentRow>('payments')
      .insert({ ...input, code })
      .returning('*');
    return rows[0];
  }

  async markPaid(paymentId: number): Promise<PaymentRow | undefined> {
    await this.db<PaymentRow>('payments')
      .where({ id: paymentId })
      .update({ status: 'paid', paid_at: this.db.fn.now(), updated_at: this.db.fn.now() });
    return this.db<PaymentRow>('payments').where({ id: paymentId }).first();
  }

  /** Ringkasan pemasukan (dibayar). Periode opsional (from/to, inklusif, YYYY-MM-DD). */
  async revenueSummary(
    from?: string,
    to?: string,
  ): Promise<{
    total_paid: number;
    count_paid: number;
    pending_count: number;
    by_method: Array<{ method: string; total: number; count: number }>;
  }> {
    const base = () => {
      const q = this.db<PaymentRow>('payments').where({ status: 'paid' });
      if (from) q.where('paid_at', '>=', `${from} 00:00:00`);
      if (to) q.where('paid_at', '<=', `${to} 23:59:59`);
      return q;
    };

    const agg = await base().count({ count: '*' }).sum({ total: 'amount' }).first();
    const pending = await this.db<PaymentRow>('payments')
      .whereNot({ status: 'paid' })
      .count({ count: '*' })
      .first();
    const byMethodRows = (await base()
      .groupBy('method')
      .select('method')
      .count({ count: '*' })
      .sum({ total: 'amount' })) as unknown as Array<{
      method: string;
      count: number | string;
      total: number | string | null;
    }>;

    return {
      total_paid: Number((agg as { total?: number | string } | undefined)?.total ?? 0),
      count_paid: Number((agg as { count?: string } | undefined)?.count ?? 0),
      pending_count: Number((pending as { count?: string } | undefined)?.count ?? 0),
      by_method: byMethodRows.map((r) => ({
        method: String(r.method),
        total: Number(r.total ?? 0),
        count: Number(r.count ?? 0),
      })),
    };
  }
}

export const paymentRepository = new PaymentRepository();
