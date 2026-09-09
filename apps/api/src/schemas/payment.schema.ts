import { SimulatePaymentRequestSchema } from '@rag-salon/shared-types';
import { z } from 'zod';

export const simulateSchema = { body: SimulatePaymentRequestSchema };
export const paymentIdSchema = { params: z.object({ id: z.string().min(1) }) };
