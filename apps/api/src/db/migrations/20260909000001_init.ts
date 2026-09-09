import type { Knex } from 'knex';

export async function up(knex: Knex): Promise<void> {
  // ---------- RBAC ----------
  await knex.schema.createTable('users', (t) => {
    t.increments('id').primary();
    t.string('name', 100).notNullable();
    t.string('email', 150).notNullable().unique();
    t.string('password_hash', 255).notNullable();
    t.smallint('type').notNullable().defaultTo(1); // 0 = superadmin, 1 = biasa
    t.string('status', 20).notNullable().defaultTo('active');
    t.timestamp('last_login_at').nullable();
    t.timestamps(true, true);
  });

  await knex.schema.createTable('roles', (t) => {
    t.increments('id').primary();
    t.string('name', 50).notNullable();
    t.string('code', 50).notNullable().unique();
    t.integer('parent_id').nullable(); // self FK
    t.smallint('type').notNullable().defaultTo(1); // 0 = system
    t.text('description').nullable();
    t.timestamps(true, true);
  });

  await knex.schema.alterTable('roles', (t) => {
    t.foreign('parent_id').references('roles.id').onDelete('SET NULL');
  });

  await knex.schema.createTable('permissions', (t) => {
    t.increments('id').primary();
    t.string('name', 100).notNullable().unique(); // "users.read"
    t.string('resource', 50).notNullable(); // "users"
    t.text('description').nullable();
    t.timestamps(true, true);
  });

  await knex.schema.createTable('user_roles', (t) => {
    t.integer('user_id').unsigned().notNullable().references('users.id').onDelete('CASCADE');
    t.integer('role_id').unsigned().notNullable().references('roles.id').onDelete('CASCADE');
    t.string('scope_type', 20).nullable();
    t.string('scope_value', 50).nullable();
    t.primary(['user_id', 'role_id']);
  });

  await knex.schema.createTable('role_permissions', (t) => {
    t.integer('role_id').unsigned().notNullable().references('roles.id').onDelete('CASCADE');
    t.integer('permission_id')
      .unsigned()
      .notNullable()
      .references('permissions.id')
      .onDelete('CASCADE');
    t.primary(['role_id', 'permission_id']);
  });

  await knex.schema.createTable('routes', (t) => {
    t.increments('id').primary();
    t.string('path', 200).notNullable();
    t.string('name', 100).notNullable();
    t.string('method', 10).nullable();
    t.timestamps(true, true);
  });

  await knex.schema.createTable('role_routes', (t) => {
    t.integer('role_id').unsigned().notNullable().references('roles.id').onDelete('CASCADE');
    t.integer('route_id').unsigned().notNullable().references('routes.id').onDelete('CASCADE');
    t.primary(['role_id', 'route_id']);
  });

  await knex.schema.createTable('menus', (t) => {
    t.increments('id').primary();
    t.string('name', 100).notNullable();
    t.string('path', 200).notNullable();
    t.string('icon', 50).nullable();
    t.integer('parent_id').unsigned().nullable();
    t.integer('sort_order').notNullable().defaultTo(0);
    t.timestamps(true, true);
  });

  await knex.schema.alterTable('menus', (t) => {
    t.foreign('parent_id').references('menus.id').onDelete('CASCADE');
  });

  await knex.schema.createTable('role_menus', (t) => {
    t.integer('role_id').unsigned().notNullable().references('roles.id').onDelete('CASCADE');
    t.integer('menu_id').unsigned().notNullable().references('menus.id').onDelete('CASCADE');
    t.primary(['role_id', 'menu_id']);
  });

  // ---------- Services / Reservations / Payments ----------
  await knex.schema.createTable('services', (t) => {
    t.increments('id').primary();
    t.string('name', 150).notNullable();
    t.string('slug', 150).notNullable().unique();
    t.integer('price').notNullable(); // dalam rupiah
    t.integer('duration_min').notNullable();
    t.text('description').nullable();
    t.string('category', 50).nullable();
    t.string('image', 255).nullable();
    t.boolean('is_active').notNullable().defaultTo(true);
    t.timestamps(true, true);
  });

  await knex.schema.createTable('reservations', (t) => {
    t.increments('id').primary();
    t.string('code', 50).notNullable().unique(); // INV-YYYYMMDD-XXX
    t.integer('user_id').unsigned().notNullable().references('users.id').onDelete('CASCADE');
    t.date('date').notNullable();
    t.time('time').notNullable();
    t.text('notes').nullable();
    t.string('status', 20).notNullable().defaultTo('pending'); // pending|confirmed|cancelled|completed
    t.integer('total').notNullable();
    t.timestamp('expires_at').nullable();
    t.timestamps(true, true);
  });
  await knex.schema.alterTable('reservations', (t) => {
    t.index('user_id');
  });

  await knex.schema.createTable('reservation_items', (t) => {
    t.increments('id').primary();
    t.integer('reservation_id')
      .unsigned()
      .notNullable()
      .references('reservations.id')
      .onDelete('CASCADE');
    t.integer('service_id').unsigned().notNullable().references('services.id').onDelete('RESTRICT');
    t.string('service_name', 150).notNullable();
    t.integer('price').notNullable();
  });

  await knex.schema.createTable('payments', (t) => {
    t.increments('id').primary();
    t.string('code', 50).notNullable().unique(); // PAY-XXXXXX
    t.integer('reservation_id')
      .unsigned()
      .notNullable()
      .references('reservations.id')
      .onDelete('CASCADE');
    t.integer('user_id').unsigned().notNullable().references('users.id').onDelete('CASCADE');
    t.string('method', 20).notNullable(); // qris|transfer|cash
    t.string('status', 20).notNullable().defaultTo('pending');
    t.integer('amount').notNullable();
    t.timestamp('paid_at').nullable();
    t.timestamps(true, true);
  });
  await knex.schema.alterTable('payments', (t) => {
    t.index('reservation_id');
  });
}

export async function down(knex: Knex): Promise<void> {
  await knex.schema.dropTableIfExists('payments');
  await knex.schema.dropTableIfExists('reservation_items');
  await knex.schema.dropTableIfExists('reservations');
  await knex.schema.dropTableIfExists('services');
  await knex.schema.dropTableIfExists('role_menus');
  await knex.schema.dropTableIfExists('menus');
  await knex.schema.dropTableIfExists('role_routes');
  await knex.schema.dropTableIfExists('routes');
  await knex.schema.dropTableIfExists('role_permissions');
  await knex.schema.dropTableIfExists('user_roles');
  await knex.schema.dropTableIfExists('permissions');
  await knex.schema.dropTableIfExists('roles');
  await knex.schema.dropTableIfExists('users');
}
