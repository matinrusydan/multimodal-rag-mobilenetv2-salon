import knex from 'knex';
import config from '../../knexfile';
import { env } from '../config/env';

const client = knex(config[env.NODE_ENV] ?? config.development);

async function run() {
  const [batch, log] = await client.migrate.latest();
  console.log(`Migrasi selesai. Batch: ${batch}, migrasi: ${log.length}`);
}

run()
  .catch((err) => {
    console.error('Migrasi gagal:', err);
    process.exit(1);
  })
  .finally(() => client.destroy());
