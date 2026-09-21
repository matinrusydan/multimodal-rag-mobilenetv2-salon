import type { Knex } from 'knex';

/**
 * Struktur menu admin: parent "Menu Admin" + children menu /admin/*.
 * Idempotent: pakai upsert berdasarkan path.
 */
const PARENT = { name: 'Menu Admin', path: '#', icon: 'folder', sort_order: 9 };

const ADMIN_MENUS: Array<{ name: string; path: string; icon: string; sort_order: number }> = [
  { name: 'Ringkasan', path: '/admin', icon: 'dashboard', sort_order: 1 },
  { name: 'Kelola Pengguna', path: '/admin/users', icon: 'users', sort_order: 2 },
  { name: 'Kelola Role', path: '/admin/roles', icon: 'shield', sort_order: 3 },
  { name: 'Permissions', path: '/admin/permissions', icon: 'key', sort_order: 4 },
  { name: 'Routes', path: '/admin/routes', icon: 'route', sort_order: 5 },
  { name: 'Menus', path: '/admin/menus', icon: 'list', sort_order: 6 },
  { name: 'Akses Menu', path: '/admin/role-menus', icon: 'shield', sort_order: 7 },
  { name: 'Layanan & Harga', path: '/admin/services', icon: 'scissors', sort_order: 8 },
  { name: 'Reservasi', path: '/admin/reservations', icon: 'calendar', sort_order: 9 },
  { name: 'Info Salon', path: '/admin/settings', icon: 'settings', sort_order: 10 },
  { name: 'Dokumen RAG', path: '/admin/knowledge', icon: 'file', sort_order: 11 },
];

export async function seed(knex: Knex): Promise<void> {
  await knex.transaction(async (trx) => {
    // Parent "Menu Admin": cari path '#' dgn nama Menu Admin, else buat.
    let parent = await trx('menus').where({ path: '#', name: PARENT.name }).first();
    if (!parent) {
      const existingHash = await trx('menus').where({ path: '#' }).first();
      if (existingHash) {
        await trx('menus').where({ id: existingHash.id }).update({
          name: PARENT.name,
          icon: PARENT.icon,
          sort_order: PARENT.sort_order,
          parent_id: null,
          status: 'active',
        });
        parent = { ...existingHash, name: PARENT.name };
      } else {
        const [inserted] = await trx('menus')
          .insert({ ...PARENT, parent_id: null, status: 'active' })
          .returning('*');
        parent = inserted;
      }
    }
    const parentId = parent.id as number;

    // Children menu admin.
    for (const menu of ADMIN_MENUS) {
      const existing = await trx('menus').where({ path: menu.path }).first();
      if (existing) {
        await trx('menus').where({ id: existing.id }).update({
          name: menu.name,
          icon: menu.icon,
          sort_order: menu.sort_order,
          parent_id: parentId,
          status: 'active',
        });
      } else {
        await trx('menus').insert({ ...menu, parent_id: parentId, status: 'active' });
      }
    }

    // Assign menu admin ke role ADMIN & SUPER_ADMIN.
    const adminRoles = await trx('roles').whereIn('code', ['ADMIN', 'SUPER_ADMIN']).select('id');
    const adminMenus = await trx('menus')
      .where((b) => b.where('parent_id', parentId).orWhere('id', parentId))
      .select('id');
    const links: Array<{ role_id: number; menu_id: number }> = [];
    for (const r of adminRoles) {
      for (const m of adminMenus) {
        links.push({ role_id: r.id, menu_id: m.id });
      }
    }
    if (links.length > 0) {
      await trx('role_menus').insert(links).onConflict(['role_id', 'menu_id']).ignore();
    }
  });
}
