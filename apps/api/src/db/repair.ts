/**
 * db/repair.ts — Perbaiki DB yang kolomnya "hilang" walau migrasi tercatat applied.
 *
 * Latar: tabel `knex_migrations` kadang sinkron (record lengkap) tetapi skema DB
 * ter-rollback/restore dari dump lama -> migrasi tidak dijalankan ulang padahal
 * kolom (status/title/parent_id/username/valid_from/valid_to) tidak ada.
 *
 * Skrip ini: hapus record migrasi reensure, jalankan migrate ulang, lalu seed.
 *
 * Usage:
 *   pnpm db:repair
 */
import knex from 'knex';
import config from '../../knexfile';
import { env } from '../config/env';

const REENSURE_MIGRATIONS = [
  '20260923000003_fix_admin_columns.ts',
  '20260924000005_reensure_admin_columns.ts',
  '20260925000006_reensure_columns.ts',
];

async function run() {
  const client = knex(config[env.NODE_ENV] ?? config.development);

  const hasKnexMig = await client.schema.hasTable('knex_migrations');
  if (hasKnexMig) {
    const deleted = await client('knex_migrations').whereIn('name', REENSURE_MIGRATIONS).del();
    console.log(`[repair] hapus record migrasi reensure: ${deleted}`);
  }

  const [batch, log] = await client.migrate.latest();
  console.log(`[repair] migrate selesai. batch=${batch}, dijalankan=${log.length}`);

  const seedResult = await client.seed.run();
  console.log(`[repair] seed selesai. dijalankan=${seedResult[0].length}`);

  await client.destroy();
}

run().catch((err) => {
  console.error('[repair] gagal:', err);
  process.exit(1);
});
