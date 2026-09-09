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
}

export const paymentRepository = new PaymentRepository();
