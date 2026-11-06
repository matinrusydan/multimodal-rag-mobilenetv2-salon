import { SimulatePaymentRequestSchema } from '@rag-salon/shared-types';
import { z } from 'zod';

export const simulateSchema = { body: SimulatePaymentRequestSchema };
export const paymentIdSchema = { params: z.object({ id: z.string().min(1) }) };
export const adminPaymentParamsSchema = {
  params: z.object({ id: z.coerce.number().int().positive() }),
};
export const adminPaymentsQuerySchema = {
  query: z.object({
    page: z.coerce.number().int().min(1).default(1),
    pageSize: z.coerce.number().int().min(1).max(100).optional(),
    limit: z.coerce.number().int().min(1).max(100).optional(),
    status: z.enum(['pending', 'paid', 'failed']).optional(),
    search: z.string().trim().max(200).optional(),
  }),
};
