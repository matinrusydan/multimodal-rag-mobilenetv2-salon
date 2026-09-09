import { db } from '../src/config/db';
import { down, up } from '../src/db/migrations/20260909000001_init';
import { seed } from '../src/db/seeds/01_base';

export async function prepareDb(): Promise<void> {
  await down(db);
  await up(db);
  await seed(db);
}
