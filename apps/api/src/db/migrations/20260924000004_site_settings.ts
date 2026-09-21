import type { Knex } from 'knex';

/** Tabel pengaturan situs (key-value JSON) untuk landing page & konfigurasi dinamis. */
export async function up(knex: Knex): Promise<void> {
  const exists = await knex.schema.hasTable('site_settings');
  if (!exists) {
    await knex.schema.createTable('site_settings', (t) => {
      t.increments('id').primary();
      t.string('key', 100).notNullable().unique();
      t.jsonb('value').nullable();
      t.timestamps(true, true);
    });
  }
}

export async function down(knex: Knex): Promise<void> {
  await knex.schema.dropTableIfExists('site_settings');
}
