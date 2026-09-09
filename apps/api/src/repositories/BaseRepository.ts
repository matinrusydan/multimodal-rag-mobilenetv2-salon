import type { Knex } from 'knex';
import { db } from '../config/db';

export abstract class BaseRepository {
  protected readonly db: Knex = db;
}
