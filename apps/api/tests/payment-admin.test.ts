import request from 'supertest';
import { beforeAll, describe, expect, it } from 'vitest';
import { createApp } from '../src/app';
import { prepareDb } from './helpers';

const app = createApp();

async function loginToken(email: string): Promise<string> {
  const res = await request(app).post('/api/auth/login').send({ email, password: 'Password123!' });
  return res.body.data.token;
}

beforeAll(async () => {
  await prepareDb();
});

describe('GET /api/payments (Admin List)', () => {
  it('menolak tanpa token (401)', async () => {
    const res = await request(app).get('/api/payments');
    expect(res.status).toBe(401);
  });

  it('menolak customer biasa tanpa broad reservation read (403)', async () => {
    const token = await loginToken('customer@rag-salon.id');
    const res = await request(app).get('/api/payments').set('Authorization', `Bearer ${token}`);
    expect(res.status).toBe(403);
  });

  it('superadmin dan admin dapat melihat daftar pembayaran terpaginasi', async () => {
    const adminToken = await loginToken('admin@rag-salon.id');
    const res = await request(app)
      .get('/api/payments?page=1&pageSize=10')
      .set('Authorization', `Bearer ${adminToken}`);

    expect(res.status).toBe(200);
    expect(res.body.ok).toBe(true);
    expect(Array.isArray(res.body.data.items)).toBe(true);
    expect(typeof res.body.data.total).toBe('number');
    expect(res.body.data.page).toBe(1);
    expect(res.body.data.pageSize).toBe(10);
  });

  it('mendukung pencarian dan limit alias', async () => {
    const adminToken = await loginToken('admin@rag-salon.id');
    const res = await request(app)
      .get('/api/payments?page=1&limit=5&status=paid')
      .set('Authorization', `Bearer ${adminToken}`);

    expect(res.status).toBe(200);
    expect(res.body.data.pageSize).toBe(5);
  });
});

describe('GET /api/payments/admin/:id', () => {
  it('mengembalikan 404 jika id pembayaran tidak ditemukan', async () => {
    const adminToken = await loginToken('admin@rag-salon.id');
    const res = await request(app)
      .get('/api/payments/admin/9999999')
      .set('Authorization', `Bearer ${adminToken}`);

    expect(res.status).toBe(404);
  });
});

describe('Menu pemisahan /admin/payments dan /payment', () => {
  it('admin menerima menu /admin/payments di bawah grup Transaksi', async () => {
    const adminToken = await loginToken('admin@rag-salon.id');
    const res = await request(app).get('/api/menus/me').set('Authorization', `Bearer ${adminToken}`);

    expect(res.status).toBe(200);
    const menus = res.body.data as Array<{ id: number; name: string; path: string; parentId: number | null }>;
    const adminPayment = menus.find((m) => m.path === '/admin/payments');
    expect(adminPayment).toBeDefined();
    expect(adminPayment?.name).toBe('Pembayaran');
    expect(adminPayment?.parentId).not.toBeNull();

    const parentGroup = menus.find((m) => m.id === adminPayment?.parentId);
    expect(parentGroup?.name).toBe('Transaksi');
  });

  it('customer menerima /payment (tanpa parent Transaksi) dan tidak menerima /admin/payments', async () => {
    const customerToken = await loginToken('customer@rag-salon.id');
    const res = await request(app).get('/api/menus/me').set('Authorization', `Bearer ${customerToken}`);

    expect(res.status).toBe(200);
    const menus = res.body.data as Array<{ id: number; name: string; path: string; parentId: number | null }>;
    const customerPayment = menus.find((m) => m.path === '/payment');
    expect(customerPayment).toBeDefined();
    expect(customerPayment?.parentId).toBeNull();

    const adminPayment = menus.find((m) => m.path === '/admin/payments');
    expect(adminPayment).toBeUndefined();
  });
});

