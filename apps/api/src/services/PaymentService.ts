import type { SimulatePaymentRequest } from '@rag-salon/shared-types';
import { type AdminPaymentRow, paymentRepository } from '../repositories/PaymentRepository';
import { reservationRepository } from '../repositories/ReservationRepository';
import { HttpError } from '../utils/problemDetails';

interface AuthLike {
  userId: number;
  permissions: string[];
  type: number;
}

export interface SimulatePaymentResult {
  paymentId: string;
  status: 'paid';
  amount: number;
  paidAt: string;
}

export interface AdminPaymentItem {
  id: number;
  code: string;
  reservationId: number;
  reservationCode: string;
  reservationDate: string;
  userId: number;
  customerName: string;
  customerEmail: string;
  serviceNames: string | null;
  method: string;
  status: string;
  amount: number;
  paidAt: string | null;
  createdAt: string;
  updatedAt: string;
}

function mapAdminPayment(row: AdminPaymentRow): AdminPaymentItem {
  return {
    id: row.id,
    code: row.code,
    reservationId: row.reservation_id,
    reservationCode: row.reservation_code,
    reservationDate: row.reservation_date,
    userId: row.user_id,
    customerName: row.customer_name,
    customerEmail: row.customer_email,
    serviceNames: row.service_names,
    method: row.method,
    status: row.status,
    amount: Number(row.amount),
    paidAt: row.paid_at,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

export class PaymentService {
  private ensureAdminAccess(auth: AuthLike, actionMessage: string) {
    const isSuper = auth.type === 0 || auth.permissions.includes('*');
    const hasBroadRead =
      auth.permissions.includes('reservations.read') ||
      auth.permissions.includes('payments.manage');
    if (!isSuper && !hasBroadRead) {
      throw new HttpError(403, `Anda tidak memiliki izin untuk ${actionMessage}`);
    }
  }

  async listAdmin(
    auth: AuthLike,
    query: { page: number; pageSize?: number; limit?: number; status?: string; search?: string },
  ): Promise<{ items: AdminPaymentItem[]; total: number; page: number; pageSize: number; limit: number }> {
    this.ensureAdminAccess(auth, 'melihat daftar pembayaran');
    const page = Math.max(1, query.page || 1);
    const pageSize = Math.min(100, Math.max(1, query.pageSize ?? query.limit ?? 20));
    const { rows, total } = await paymentRepository.listAdmin({
      page,
      pageSize,
      status: query.status,
      search: query.search,
    });
    return {
      items: rows.map(mapAdminPayment),
      total,
      page,
      pageSize,
      limit: pageSize,
    };
  }

  async detailAdmin(auth: AuthLike, id: number): Promise<AdminPaymentItem> {
    this.ensureAdminAccess(auth, 'melihat detail pembayaran');
    const row = await paymentRepository.findAdminById(id);
    if (!row) {
      throw new HttpError(404, 'Pembayaran tidak ditemukan');
    }
    return mapAdminPayment(row);
  }

  async simulate(auth: AuthLike, input: SimulatePaymentRequest): Promise<SimulatePaymentResult> {
    const reservation = await reservationRepository.findByCode(input.reservationId);
    if (!reservation) {
      throw new HttpError(404, 'Reservasi tidak ditemukan');
    }
    if (
      auth.type !== 0 &&
      !auth.permissions.includes('reservations.read') &&
      reservation.user_id !== auth.userId
    ) {
      throw new HttpError(403, 'Anda tidak memiliki izin untuk aksi ini');
    }
    if (reservation.status === 'cancelled') {
      throw new HttpError(409, 'Reservasi dibatalkan, tidak dapat dibayar');
    }

    const existing = await paymentRepository.findByReservationId(reservation.id);
    if (existing?.status === 'paid') {
      throw new HttpError(409, 'Reservasi sudah dibayar');
    }

    const payment =
      existing ??
      (await paymentRepository.create({
        reservation_id: reservation.id,
        user_id: auth.userId,
        method: input.method,
        amount: reservation.total,
      }));
    const paid = await paymentRepository.markPaid(payment.id);
    if (!paid) throw new HttpError(500, 'Gagal memproses pembayaran');

    await reservationRepository.updateStatus(reservation.id, 'confirmed');

    return {
      paymentId: paid.code,
      status: 'paid',
      amount: paid.amount,
      paidAt: paid.paid_at ?? new Date().toISOString(),
    };
  }

  async status(
    reservationCode: string,
  ): Promise<{ paymentId: string; status: string; amount: number }> {
    const reservation = await reservationRepository.findByCode(reservationCode);
    if (!reservation) {
      throw new HttpError(404, 'Reservasi tidak ditemukan');
    }
    const payment = await paymentRepository.findByReservationId(reservation.id);
    if (!payment) {
      throw new HttpError(404, 'Pembayaran belum dibuat');
    }
    return { paymentId: payment.code, status: payment.status, amount: payment.amount };
  }

  /** Ringkasan pemasukan untuk agent admin / dashboard. */
  async summary(from?: string, to?: string): Promise<{
    totalPaid: number;
    countPaid: number;
    pendingCount: number;
    period: { from: string | null; to: string | null };
    byMethod: Array<{ method: string; total: number; count: number }>;
  }> {
    const s = await paymentRepository.revenueSummary(from, to);
    return {
      totalPaid: s.total_paid,
      countPaid: s.count_paid,
      pendingCount: s.pending_count,
      period: { from: from ?? null, to: to ?? null },
      byMethod: s.by_method,
    };
  }
}

export const paymentService = new PaymentService();
