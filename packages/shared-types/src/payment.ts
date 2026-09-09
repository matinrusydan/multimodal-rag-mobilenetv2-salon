import { z } from 'zod';

export const PaymentMethodSchema = z.enum(['qris', 'transfer', 'cash']);
export type PaymentMethod = z.infer<typeof PaymentMethodSchema>;

export const PaymentStatusSchema = z.enum(['pending', 'paid', 'failed', 'expired']);
export type PaymentStatus = z.infer<typeof PaymentStatusSchema>;

export const SimulatePaymentRequestSchema = z.object({
  reservationId: z.string().min(1),
  method: PaymentMethodSchema,
});
export type SimulatePaymentRequest = z.infer<typeof SimulatePaymentRequestSchema>;

export const PaymentSchema = z.object({
  id: z.string(),
  reservationId: z.string(),
  method: PaymentMethodSchema,
  status: PaymentStatusSchema,
  amount: z.number().nonnegative(),
  paidAt: z.string().optional(),
});
export type Payment = z.infer<typeof PaymentSchema>;
