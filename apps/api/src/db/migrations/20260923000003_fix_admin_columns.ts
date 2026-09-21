import type { Knex } from 'knex';

/**
 * Memastikan kolom panel admin benar-benar ada (idempotent via IF NOT EXISTS).
 * Migrasi sebelumnya (20260923000002) tercatat "selesai" tetapi kolomnya tidak
 * terbentuk karena pengecekan hasColumn; migrasi ini memperbaikinya dengan raw SQL.
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

  // FK parent_id (bila belum ada).
  await knex.raw(`
    DO $$
    BEGIN
      IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'routes_parent_id_foreign'
      ) THEN
        ALTER TABLE routes
          ADD CONSTRAINT routes_parent_id_foreign
          FOREIGN KEY (parent_id) REFERENCES routes(id) ON DELETE SET NULL;
      END IF;
    END $$;
  `);

  // Unique username (bila belum ada).
  await knex.raw(`
    DO $$
    BEGIN
      IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'users_username_unique'
      ) THEN
        ALTER TABLE users ADD CONSTRAINT users_username_unique UNIQUE (username);
      END IF;
    END $$;
  `);
}

export async function down(knex: Knex): Promise<void> {
  await knex.raw(`
    ALTER TABLE users
      DROP COLUMN IF EXISTS username,
      DROP COLUMN IF EXISTS valid_from,
      DROP COLUMN IF EXISTS valid_to;
  `);
  await knex.raw(`ALTER TABLE roles DROP COLUMN IF EXISTS status;`);
  await knex.raw(`
    ALTER TABLE routes
      DROP COLUMN IF EXISTS title,
      DROP COLUMN IF EXISTS parent_id,
      DROP COLUMN IF EXISTS status;
  `);
  await knex.raw(`ALTER TABLE menus DROP COLUMN IF EXISTS status;`);
}
