import type { Knex } from 'knex';
import { env } from './src/config/env';

const config: Record<string, Knex.Config> = {
  development: {
    client: env.DB_CLIENT,
    connection: env.DATABASE_URL,
    pool: { min: env.DB_POOL_MIN, max: env.DB_POOL_MAX },
    migrations: {
      directory: './src/db/migrations',
      extension: 'ts',
    },
    seeds: {
      directory: './src/db/seeds',
      extension: 'ts',
    },
  },
  test: {
    client: env.DB_CLIENT,
    connection: env.DATABASE_URL,
    pool: { min: 0, max: 5 },
    migrations: {
      directory: './src/db/migrations',
      extension: 'ts',
    },
  },
  production: {
    client: env.DB_CLIENT,
    connection: env.DATABASE_URL,
    pool: { min: env.DB_POOL_MIN, max: env.DB_POOL_MAX },
    migrations: {
      directory: './src/db/migrations',
      extension: 'ts',
    },
    seeds: {
      directory: './src/db/seeds',
      extension: 'ts',
    },
  },
};

export default config;
