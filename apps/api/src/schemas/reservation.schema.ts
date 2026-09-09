import { CreateReservationRequestSchema } from '@rag-salon/shared-types';
import { z } from 'zod';

export const idParamSchema = z.object({ id: z.coerce.number().int().positive() });
export const codeParamSchema = z.object({ code: z.string().min(1) });

export const createReservationSchema = { body: CreateReservationRequestSchema };
export const reservationIdSchema = { params: idParamSchema };
export const reservationCodeSchema = { params: codeParamSchema };
