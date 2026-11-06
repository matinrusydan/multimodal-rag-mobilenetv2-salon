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

export interface AdminPaymentRow extends PaymentRow {
  reservation_code: string;
  reservation_date: string;
  customer_id: number;
  customer_name: string;
  customer_email: string;
  service_names: string | null;
}

export class PaymentRepository extends BaseRepository {
  private adminQuery() {
    return this.db('payments as p')
      .join('reservations as r', 'r.id', 'p.reservation_id')
      .join('users as u', 'u.id', 'p.user_id')
      .leftJoin('reservation_items as ri', 'ri.reservation_id', 'r.id')
      .select(
        'p.id',
        'p.code',
        'p.reservation_id',
        'p.user_id',
        'p.method',
        'p.status',
        'p.amount',
        'p.paid_at',
        'p.created_at',
        'p.updated_at',
        'r.code as reservation_code',
        'r.date as reservation_date',
        'u.id as customer_id',
        'u.name as customer_name',
        'u.email as customer_email',
        this.db.raw("string_agg(DISTINCT ri.service_name, ', ') as service_names"),
      )
      .groupBy(
        'p.id',
        'p.code',
        'p.reservation_id',
        'p.user_id',
        'p.method',
        'p.status',
        'p.amount',
        'p.paid_at',
        'p.created_at',
        'p.updated_at',
        'r.code',
        'r.date',
        'u.id',
        'u.name',
        'u.email',
      );
  }

  async listAdmin(input: { page: number; pageSize: number; status?: string; search?: string }): Promise<{ rows: AdminPaymentRow[]; total: number }> {
    const applyFilters = (query: any) => {
      if (input.status) query.where('p.status', input.status);
      if (input.search) {
        const term = `%${input.search}%`;
        query.where((builder: any) => builder.whereILike('p.code', term)
          .orWhereILike('u.name', term).orWhereILike('u.email', term).orWhereILike('r.code', term));
      }
      return query;
    };
    const count = applyFilters(this.db('payments as p').join('reservations as r', 'r.id', 'p.reservation_id').join('users as u', 'u.id', 'p.user_id'));
    const totalRow = await count.countDistinct({ total: 'p.id' }).first() as { total?: number | string };
    const rows = await applyFilters(this.adminQuery()).orderBy('p.created_at', 'desc')
      .limit(input.pageSize).offset((input.page - 1) * input.pageSize) as AdminPaymentRow[];
    return { rows, total: Number(totalRow?.total ?? 0) };
  }

  async findAdminById(id: number): Promise<AdminPaymentRow | undefined> {
    return this.adminQuery().where('p.id', id).first() as Promise<AdminPaymentRow | undefined>;
  }

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
