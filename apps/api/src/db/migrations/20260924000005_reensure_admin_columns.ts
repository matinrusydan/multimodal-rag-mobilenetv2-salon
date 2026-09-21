import type { Knex } from 'knex';

/**
 * Re-ensure semua kolom panel admin (idempotent). Dibuat karena migrasi
 * sebelumnya tercatat "selesai" namun kolomnya hilang (kemungkinan DB di-reset).
 */
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
  await knex.raw(`
    DO $$
    BEGIN
      IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints WHERE constraint_name = 'users_username_unique') THEN
        ALTER TABLE users ADD CONSTRAINT users_username_unique UNIQUE (username);
      END IF;
      IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints WHERE constraint_name = 'routes_parent_id_foreign') THEN
        ALTER TABLE routes ADD CONSTRAINT routes_parent_id_foreign FOREIGN KEY (parent_id) REFERENCES routes(id) ON DELETE SET NULL;
      END IF;
    END $$;
  `);
}

export async function down(): Promise<void> {
  // no-op (perbaikan kolom)
}
