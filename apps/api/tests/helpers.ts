import { db } from '../src/config/db';
import { down, up } from '../src/db/migrations/20260909000001_init';
import { seed as seedBase } from '../src/db/seeds/01_base';
import { seed as seedTree } from '../src/db/seeds/02_admin_menu_tree';

export async function prepareDb(): Promise<void> {
  await down(db);
  await up(db);
  await db.raw(`
    ALTER TABLE users
      ADD COLUMN IF NOT EXISTS username varchar(100),
      ADD COLUMN IF NOT EXISTS valid_from date,
      ADD COLUMN IF NOT EXISTS valid_to date;
    ALTER TABLE roles
      ADD COLUMN IF NOT EXISTS status varchar(20) NOT NULL DEFAULT 'active';
    ALTER TABLE routes
      ADD COLUMN IF NOT EXISTS title varchar(150),
      ADD COLUMN IF NOT EXISTS parent_id integer,
      ADD COLUMN IF NOT EXISTS status varchar(20) NOT NULL DEFAULT 'active';
    ALTER TABLE menus
      ADD COLUMN IF NOT EXISTS status varchar(20) NOT NULL DEFAULT 'active';
  `);
  await seedBase(db);
  await seedTree(db);
}


