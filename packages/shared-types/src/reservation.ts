import { z } from 'zod';

export const ReservationStatusSchema = z.enum(['pending', 'confirmed', 'cancelled', 'completed']);
export type ReservationStatus = z.infer<typeof ReservationStatusSchema>;

export const CreateReservationRequestSchema = z.object({
  serviceIds: z.array(z.number().int().positive()).min(1, 'Pilih minimal satu layanan'),
  date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'Format tanggal tidak valid'),
  time: z.string().regex(/^\d{2}:\d{2}$/, 'Format waktu tidak valid'),
  notes: z.string().max(500).optional(),
});
export type CreateReservationRequest = z.infer<typeof CreateReservationRequestSchema>;

export const ReservationItemSchema = z.object({
  serviceId: z.number().int().positive(),
  serviceName: z.string(),
  price: z.number().nonnegative(),
});
export type ReservationItem = z.infer<typeof ReservationItemSchema>;

export const ReservationSchema = z.object({
  id: z.string(),
  userId: z.number().int().positive(),
  items: z.array(ReservationItemSchema),
  total: z.number().nonnegative(),
  date: z.string(),
  time: z.string(),
  notes: z.string().optional(),
  status: ReservationStatusSchema,
  createdAt: z.string(),
});
export type Reservation = z.infer<typeof ReservationSchema>;
