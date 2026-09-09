import type { SimulatePaymentRequest } from '@rag-salon/shared-types';
import { paymentRepository } from '../repositories/PaymentRepository';
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

export class PaymentService {
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
}

export const paymentService = new PaymentService();
