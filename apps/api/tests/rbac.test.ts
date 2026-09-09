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

describe('RBAC enforcement', () => {
  it('endpoint admin tanpa token → 401', async () => {
    const res = await request(app).get('/api/users');
    expect(res.status).toBe(401);
  });

  it('customer tanpa users.read → 403', async () => {
    const token = await loginToken('customer@rag-salon.id');
    const res = await request(app).get('/api/users').set('Authorization', `Bearer ${token}`);
    expect(res.status).toBe(403);
    expect(res.body.type).toBe('about:blank#403');
  });

  it('staff tanpa users.manage → 403 saat assign role', async () => {
    const token = await loginToken('staff@rag-salon.id');
    const res = await request(app)
      .put('/api/users/3/roles')
      .set('Authorization', `Bearer ${token}`)
      .send({ roleIds: [1] });
    expect(res.status).toBe(403);
  });

  it('superadmin (type 0) bypass → 200', async () => {
    const token = await loginToken('admin@rag-salon.id');
    const res = await request(app).get('/api/users').set('Authorization', `Bearer ${token}`);
    expect(res.status).toBe(200);
    expect(res.body.data).toHaveLength(3);
  });

  it('permission wildcard users.manage memungkinkan assign role', async () => {
    const token = await loginToken('admin@rag-salon.id');
    const res = await request(app)
      .put('/api/users/2/roles')
      .set('Authorization', `Bearer ${token}`)
      .send({ roleIds: [1, 3] });
    expect(res.status).toBe(200);
    expect(res.body.data.roles).toEqual(expect.arrayContaining(['SUPER_ADMIN', 'STAFF']));
  });

  it('staff dapat membaca semua reservasi (reservations.read)', async () => {
    const token = await loginToken('staff@rag-salon.id');
    const res = await request(app).get('/api/reservations').set('Authorization', `Bearer ${token}`);
    expect(res.status).toBe(200);
  });
});

describe('Permission list via session', () => {
  it('session customer berisi permissions role-nya', async () => {
    const token = await loginToken('customer@rag-salon.id');
    const res = await request(app).get('/api/auth/session').set('Authorization', `Bearer ${token}`);
    expect(res.status).toBe(200);
    expect(res.body.data.permissions).toContain('reservations.create');
    expect(res.body.data.permissions).not.toContain('users.read');
    expect(res.body.data.roles.map((role: { code: string }) => role.code)).toEqual(['CUSTOMER']);
  });
});
