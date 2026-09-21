import type { Knex } from 'knex';

/**
 * Tambahan kolom untuk panel admin (RBAC + user validity).
 * Idempotent: cek hasColumn sebelum menambah.
 */
export async function up(knex: Knex): Promise<void> {
  // ---- users: username, valid_from, valid_to ----
  const hasUsername = await knex.schema.hasColumn('users', 'username');
  if (!hasUsername) {
    await knex.schema.alterTable('users', (t) => {
      t.string('username', 100).nullable();
      t.date('valid_from').nullable();
      t.date('valid_to').nullable();
    });
    await knex.schema.alterTable('users', (t) => {
      t.unique(['username']);
    });
  }

  // ---- roles: status ----
  if (!(await knex.schema.hasColumn('roles', 'status'))) {
    await knex.schema.alterTable('roles', (t) => {
      t.string('status', 20).notNullable().defaultTo('active');
    });
  }

  // ---- routes: title, parent_id, status ----
  if (!(await knex.schema.hasColumn('routes', 'title'))) {
    await knex.schema.alterTable('routes', (t) => {
      t.string('title', 150).nullable();
      t.integer('parent_id').unsigned().nullable();
      t.string('status', 20).notNullable().defaultTo('active');
    });
    await knex.schema.alterTable('routes', (t) => {
      t.foreign('parent_id').references('routes.id').onDelete('SET NULL');
    });
  }

  // ---- menus: status ----
  if (!(await knex.schema.hasColumn('menus', 'status'))) {
    await knex.schema.alterTable('menus', (t) => {
      t.string('status', 20).notNullable().defaultTo('active');
    });
  }
}

export async function down(knex: Knex): Promise<void> {
  if (await knex.schema.hasColumn('users', 'username')) {
    await knex.schema.alterTable('users', (t) => {
      t.dropColumn('username');
      t.dropColumn('valid_from');
      t.dropColumn('valid_to');
    });
  }
  if (await knex.schema.hasColumn('roles', 'status')) {
    await knex.schema.alterTable('roles', (t) => t.dropColumn('status'));
  }
  if (await knex.schema.hasColumn('routes', 'title')) {
    await knex.schema.alterTable('routes', (t) => {
      t.dropForeign(['parent_id']);
      t.dropColumn('title');
      t.dropColumn('parent_id');
      t.dropColumn('status');
    });
  }
  if (await knex.schema.hasColumn('menus', 'status')) {
    await knex.schema.alterTable('menus', (t) => t.dropColumn('status'));
  }
}
