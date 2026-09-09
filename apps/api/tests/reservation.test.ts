import request from 'supertest';
import { beforeAll, describe, expect, it } from 'vitest';
import { createApp } from '../src/app';
import { prepareDb } from './helpers';

const app = createApp();

async function loginToken(email: string): Promise<string> {
  const res = await request(app).post('/api/auth/login').send({ email, password: 'Password123!' });
  return res.body.data.token;
}

async function createReservation(token: string, serviceIds: number[] = [1]) {
  return request(app)
    .post('/api/reservations')
    .set('Authorization', `Bearer ${token}`)
    .send({ serviceIds, date: '2026-09-20', time: '14:00', notes: 'Minta stylist ramah' });
}

beforeAll(async () => {
  await prepareDb();
});

describe('POST /api/reservations', () => {
  it('customer membuat reservasi', async () => {
    const token = await loginToken('customer@rag-salon.id');
    const res = await createReservation(token, [2, 6]);
    expect(res.status).toBe(201);
    expect(res.body.data.id).toMatch(/^INV-\d{8}-\d{3}$/);
    expect(res.body.data.total).toBe(500000);
    expect(res.body.data.items).toHaveLength(2);
    expect(res.body.data.status).toBe('pending');
  });

  it('menolak tanpa token (401)', async () => {
    const res = await createReservation('invalid-token');
    expect(res.status).toBe(401);
  });

  it('saldo service tidak lengkap → 400', async () => {
    const token = await loginToken('customer@rag-salon.id');
    const res = await createReservation(token, [1, 999]);
    expect(res.status).toBe(400);
  });
});

describe('GET /api/reservations', () => {
  it('customer hanya melihat reservasi miliknya', async () => {
    const token = await loginToken('customer@rag-salon.id');
    await createReservation(token, [1]);
    const res = await request(app).get('/api/reservations').set('Authorization', `Bearer ${token}`);
    expect(res.status).toBe(200);
    expect(res.body.data.length).toBeGreaterThan(0);
    for (const item of res.body.data) {
      expect(item.userId).toBe(res.body.data[0]?.userId);
    }
  });

  it('staff melihat semua reservasi', async () => {
    const token = await loginToken('staff@rag-salon.id');
    const res = await request(app).get('/api/reservations').set('Authorization', `Bearer ${token}`);
    expect(res.status).toBe(200);
    expect(Array.isArray(res.body.data)).toBe(true);
  });
});

describe('GET /api/reservations/:code', () => {
  it('pemilik reservasi melihat detail', async () => {
    const token = await loginToken('customer@rag-salon.id');
    const created = await createReservation(token, [1]);
    const res = await request(app)
      .get(`/api/reservations/${created.body.data.id}`)
      .set('Authorization', `Bearer ${token}`);
    expect(res.status).toBe(200);
    expect(res.body.data.id).toBe(created.body.data.id);
  });

  it('customer tidak bisa melihat reservasi orang lain (403)', async () => {
    const owner = await loginToken('staff@rag-salon.id');
    const other = await loginToken('customer@rag-salon.id');
    const created = await createReservation(owner, [1]);
    const res = await request(app)
      .get(`/api/reservations/${created.body.data.id}`)
      .set('Authorization', `Bearer ${other}`);
    expect(res.status).toBe(403);
  });
});

describe('PUT /api/reservations/:code/cancel', () => {
  it('staff membatalkan reservasi', async () => {
    const customer = await loginToken('customer@rag-salon.id');
    const created = await createReservation(customer, [1]);
    const staff = await loginToken('staff@rag-salon.id');
    const res = await request(app)
      .put(`/api/reservations/${created.body.data.id}/cancel`)
      .set('Authorization', `Bearer ${staff}`)
      .send({});
    expect(res.status).toBe(200);
    expect(res.body.data.status).toBe('cancelled');
  });

  it('customer tidak bisa membatalkan (403)', async () => {
    const customer = await loginToken('customer@rag-salon.id');
    const created = await createReservation(customer, [1]);
    const res = await request(app)
      .put(`/api/reservations/${created.body.data.id}/cancel`)
      .set('Authorization', `Bearer ${customer}`)
      .send({});
    expect(res.status).toBe(403);
  });

  it('kode tidak ada → 404', async () => {
    const staff = await loginToken('staff@rag-salon.id');
    const res = await request(app)
      .put('/api/reservations/INV-00000000-000/cancel')
      .set('Authorization', `Bearer ${staff}`)
      .send({});
    expect(res.status).toBe(404);
  });
});
