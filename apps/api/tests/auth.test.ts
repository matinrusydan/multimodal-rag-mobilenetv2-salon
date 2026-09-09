import request from 'supertest';
import { beforeAll, describe, expect, it } from 'vitest';
import { createApp } from '../src/app';
import { prepareDb } from './helpers';

const app = createApp();

beforeAll(async () => {
  await prepareDb();
});

describe('POST /api/auth/register', () => {
  it('mendaftarkan akun customer baru', async () => {
    const res = await request(app).post('/api/auth/register').send({
      name: 'Siti Aminah',
      email: 'siti@example.com',
      password: 'Rahasia123',
    });
    expect(res.status).toBe(201);
    expect(res.body.ok).toBe(true);
    expect(res.body.data.token).toBeTruthy();
    expect(res.body.data.user.email).toBe('siti@example.com');
    expect(res.body.data.user.roles.map((role: { code: string }) => role.code)).toEqual([
      'CUSTOMER',
    ]);
  });

  it('menolak email duplikat dengan 409', async () => {
    const res = await request(app).post('/api/auth/register').send({
      name: 'Duplikat',
      email: 'customer@rag-salon.id',
      password: 'Rahasia123',
    });
    expect(res.status).toBe(409);
    expect(res.body.title).toBeTruthy();
  });

  it('menolak input tidak valid dengan 400', async () => {
    const res = await request(app).post('/api/auth/register').send({
      name: '',
      email: 'bukan-email',
      password: '123',
    });
    expect(res.status).toBe(400);
    expect(res.body.type).toBe('about:blank#400');
  });
});

describe('POST /api/auth/login', () => {
  it('berhasil login customer seed', async () => {
    const res = await request(app).post('/api/auth/login').send({
      email: 'customer@rag-salon.id',
      password: 'Password123!',
    });
    expect(res.status).toBe(200);
    expect(res.body.data.token).toBeTruthy();
    expect(res.body.data.user.roles.map((role: { code: string }) => role.code)).toEqual([
      'CUSTOMER',
    ]);
  });

  it('menolak password salah dengan 401', async () => {
    const res = await request(app).post('/api/auth/login').send({
      email: 'customer@rag-salon.id',
      password: 'salah',
    });
    expect(res.status).toBe(401);
  });
});

describe('GET /api/auth/session', () => {
  it('sinkronisasi session user terautentikasi', async () => {
    const login = await request(app).post('/api/auth/login').send({
      email: 'staff@rag-salon.id',
      password: 'Password123!',
    });
    const token = login.body.data.token;
    const res = await request(app).get('/api/auth/session').set('Authorization', `Bearer ${token}`);
    expect(res.status).toBe(200);
    expect(res.body.data.permissions).toContain('reservations.read');
  });

  it('menolak tanpa token (401)', async () => {
    const res = await request(app).get('/api/auth/session');
    expect(res.status).toBe(401);
  });
});
