import type { Knex } from 'knex';

/** Pastikan kolom panel admin + site_settings ada (idempotent). */
export async function up(knex: Knex): Promise<void> {
  await knex.raw(`
    ALTER TABLE users
      ADD COLUMN IF NOT EXISTS username varchar(100),
      ADD COLUMN IF NOT EXISTS valid_from date,
      ADD COLUMN IF NOT EXISTS valid_to date;
  `);
  await knex.raw(`
    ALTER TABLE roles
      ADD COLUMN IF NOT EXISTS status varchar(20) NOT NULL DEFAULT 'active';
  `);
  await knex.raw(`
    ALTER TABLE routes
      ADD COLUMN IF NOT EXISTS title varchar(150),
      ADD COLUMN IF NOT EXISTS parent_id integer,
      ADD COLUMN IF NOT EXISTS status varchar(20) NOT NULL DEFAULT 'active';
  `);
  await knex.raw(`
    ALTER TABLE menus
      ADD COLUMN IF NOT EXISTS status varchar(20) NOT NULL DEFAULT 'active';
  `);
}

export async function down(): Promise<void> {
  // no-op
}
