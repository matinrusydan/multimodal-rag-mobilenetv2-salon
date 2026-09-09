import request from 'supertest';
import { beforeAll, describe, expect, it } from 'vitest';
import { createApp } from '../src/app';
import { prepareDb } from './helpers';

const app = createApp();

const PNG_1X1 = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=',
  'base64',
);

async function loginToken(email: string): Promise<string> {
  const res = await request(app).post('/api/auth/login').send({ email, password: 'Password123!' });
  return res.body.data.token;
}

async function createReservation(token: string) {
  return request(app)
    .post('/api/reservations')
    .set('Authorization', `Bearer ${token}`)
    .send({ serviceIds: [1], date: '2026-09-21', time: '10:00' });
}

beforeAll(async () => {
  await prepareDb();
});

describe('POST /api/payments/simulate', () => {
  it('pemilik reservasi membayar → status paid & reservasi confirmed', async () => {
    const token = await loginToken('customer@rag-salon.id');
    const created = await createReservation(token);
    const code = created.body.data.id;

    const res = await request(app)
      .post('/api/payments/simulate')
      .set('Authorization', `Bearer ${token}`)
      .send({ reservationId: code, method: 'qris' });
    expect(res.status).toBe(200);
    expect(res.body.data.status).toBe('paid');
    expect(res.body.data.paymentId).toMatch(/^PAY-\d{6}$/);

    const detail = await request(app)
      .get(`/api/reservations/${code}`)
      .set('Authorization', `Bearer ${token}`);
    expect(detail.body.data.status).toBe('confirmed');
  });

  it('pembayaran berulang → 409', async () => {
    const token = await loginToken('customer@rag-salon.id');
    const created = await createReservation(token);
    const code = created.body.data.id;
    await request(app)
      .post('/api/payments/simulate')
      .set('Authorization', `Bearer ${token}`)
      .send({ reservationId: code, method: 'qris' });
    const res = await request(app)
      .post('/api/payments/simulate')
      .set('Authorization', `Bearer ${token}`)
      .send({ reservationId: code, method: 'qris' });
    expect(res.status).toBe(409);
  });

  it('customer tidak bisa bayar reservasi orang lain → 403', async () => {
    const owner = await loginToken('staff@rag-salon.id');
    const intruder = await loginToken('customer@rag-salon.id');
    const created = await createReservation(owner);
    const res = await request(app)
      .post('/api/payments/simulate')
      .set('Authorization', `Bearer ${intruder}`)
      .send({ reservationId: created.body.data.id, method: 'qris' });
    expect(res.status).toBe(403);
  });
});

describe('Rate limit /api/analyze', () => {
  it('melewati batas → 429 Too Many Requests', async () => {
    for (let i = 0; i < 30; i += 1) {
      await request(app)
        .post('/api/analyze')
        .set('Content-Type', 'multipart/form-data')
        .attach('image', PNG_1X1, { filename: 'hair.png', contentType: 'image/png' });
    }
    const res = await request(app)
      .post('/api/analyze')
      .set('Content-Type', 'multipart/form-data')
      .attach('image', PNG_1X1, { filename: 'hair.png', contentType: 'image/png' });
    expect(res.status).toBe(429);
  });
});
