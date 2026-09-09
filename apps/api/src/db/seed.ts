import knex from 'knex';
import config from '../../knexfile';
import { env } from '../config/env';

const client = knex(config[env.NODE_ENV] ?? config.development);

async function run() {
  await client.seed.run();
  console.log('Seed selesai.');
}

run()
  .catch((err) => {
    console.error('Seed gagal:', err);
    process.exit(1);
  })
  .finally(() => client.destroy());
