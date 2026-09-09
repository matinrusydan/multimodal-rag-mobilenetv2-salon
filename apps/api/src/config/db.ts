import knex from 'knex';
import { env } from './env';

export const createDb = () =>
  knex({
    client: env.DB_CLIENT,
    connection: env.DATABASE_URL,
    pool: { min: env.DB_POOL_MIN, max: env.DB_POOL_MAX },
  });

export const db = createDb();

export async function pingDb(): Promise<boolean> {
  try {
    await db.raw('SELECT 1');
    return true;
  } catch {
    return false;
  }
}
