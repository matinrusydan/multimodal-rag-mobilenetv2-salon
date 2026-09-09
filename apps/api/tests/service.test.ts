import request from 'supertest';
import { beforeAll, describe, expect, it } from 'vitest';
import { createApp } from '../src/app';
import { prepareDb } from './helpers';

const app = createApp();

beforeAll(async () => {
  await prepareDb();
});

describe('GET /api/services', () => {
  it('mengembalikan daftar layanan publik', async () => {
    const res = await request(app).get('/api/services');
    expect(res.status).toBe(200);
    expect(res.body.ok).toBe(true);
    expect(res.body.data.length).toBeGreaterThanOrEqual(6);
    expect(res.body.data[0]).toMatchObject({
      id: expect.any(Number),
      name: expect.any(String),
      slug: expect.any(String),
      price: expect.any(Number),
      durationMin: expect.any(Number),
    });
  });
});

describe('GET /api/services/:slug', () => {
  it('mengembalikan detail layanan', async () => {
    const res = await request(app).get('/api/services/precision-haircut');
    expect(res.status).toBe(200);
    expect(res.body.data.name).toBe('Precision Haircut');
  });

  it('404 untuk slug tidak ada', async () => {
    const res = await request(app).get('/api/services/tidak-ada');
    expect(res.status).toBe(404);
  });
});
