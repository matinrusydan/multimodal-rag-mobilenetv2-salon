/** Export only public service fields in a read-only repeatable-read transaction. */
import { config } from 'dotenv';
import pg from 'pg';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import { mkdir, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';

const here = dirname(fileURLToPath(import.meta.url));
config({ path: resolve(here, '../.env') });
const destination = resolve(here, '../../ai/rag/eval/pilot/services.snapshot.json');
if (process.argv.includes('--help')) {
  console.log('node apps/api/tools/export_rag_pilot.mjs\nEkspor SELECT read-only tabel services ke apps/ai/rag/eval/pilot/services.snapshot.json.');
  process.exit(0);
}
const client = new pg.Client({ connectionString: process.env.DATABASE_URL, connectionTimeoutMillis: 4000, statement_timeout: 5000 });
try {
  if (!process.env.DATABASE_URL) throw Object.assign(new Error('Missing configuration'), { code: 'MISSING_DATABASE_URL' });
  await client.connect();
  await client.query('BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY');
  const clock = await client.query('SELECT transaction_timestamp() AS captured_at');
  const { rows } = await client.query('SELECT id, name, slug, price, duration_min, description, category, is_active, updated_at FROM services WHERE is_active = true ORDER BY id');
  await client.query('COMMIT');
  const body = JSON.stringify(rows);
  const snapshot = { schema_version: 1, status: 'captured', source: 'postgresql.services', transaction: 'repeatable_read_read_only', captured_at: clock.rows[0].captured_at, records_sha256: createHash('sha256').update(body).digest('hex'), records: rows };
  await mkdir(dirname(destination), { recursive: true });
  await writeFile(destination, JSON.stringify(snapshot, null, 2) + '\n', 'utf8');
  console.log(JSON.stringify({ status: snapshot.status, records: rows.length, sha256: snapshot.records_sha256, output: destination }));
} catch (error) {
  // Do not expose connection strings, environment variables or server error text.
  console.error(JSON.stringify({ status: 'unavailable', code: error.code || 'DATABASE_READ_FAILED' }));
  process.exitCode = 1;
} finally {
  await client.end().catch(() => {});
}
