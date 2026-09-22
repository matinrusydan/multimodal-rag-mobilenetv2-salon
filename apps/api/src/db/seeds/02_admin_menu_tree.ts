import type { Knex } from 'knex';

/**
 * Struktur menu admin modular: beberapa grup (judul teks) + item di dalamnya.
 * Grup = parent dengan icon null & path '#' -> dirender sebagai judul grup.
 * Idempotent: upsert berdasarkan path.
 */

interface MenuDef {
  name: string;
  path: string;
  icon: string | null;
  sort_order: number;
}

/** Grup (judul) + item-itemnya. */
const GROUPS: Array<{ group: MenuDef; items: MenuDef[] }> = [
  {
    group: { name: 'Dashboard', path: '#', icon: null, sort_order: 1 },
    items: [{ name: 'Dashboard', path: '/admin', icon: 'dashboard', sort_order: 1 }],
  },
  {
    group: { name: 'Manajemen Salon', path: '#', icon: null, sort_order: 2 },
    items: [
      { name: 'Layanan & Harga', path: '/admin/services', icon: 'scissors', sort_order: 1 },
      { name: 'Reservasi', path: '/admin/reservations', icon: 'calendar', sort_order: 2 },
    ],
  },
  {
    group: { name: 'Konten & Info', path: '#', icon: null, sort_order: 3 },
    items: [
      { name: 'Info Salon', path: '/admin/settings', icon: 'settings', sort_order: 1 },
      { name: 'Dokumen RAG', path: '/admin/knowledge', icon: 'file', sort_order: 2 },
    ],
  },
  {
    group: { name: 'Akses & Keamanan', path: '#', icon: null, sort_order: 4 },
    items: [
      { name: 'Pengguna', path: '/admin/users', icon: 'users', sort_order: 1 },
      { name: 'Role', path: '/admin/roles', icon: 'shield', sort_order: 2 },
      { name: 'Permissions', path: '/admin/permissions', icon: 'key', sort_order: 3 },
      { name: 'Routes', path: '/admin/routes', icon: 'route', sort_order: 4 },
      { name: 'Menus', path: '/admin/menus', icon: 'list', sort_order: 5 },
      { name: 'Akses Menu', path: '/admin/role-menus', icon: 'shield', sort_order: 6 },
    ],
  },
];

export async function seed(knex: Knex): Promise<void> {
  await knex.transaction(async (trx) => {
    const allMenuIds: number[] = [];
    const groupNames = GROUPS.map((g) => g.group.name);

    // Bersihkan grup lama: non-aktifkan path '#' yang namanya bukan grup baru.
    await trx('menus')
      .where({ path: '#' })
      .whereNotIn('name', groupNames)
      .update({ status: 'inactive', parent_id: null });

    for (const { group, items } of GROUPS) {
      // Grup: cari berdasarkan nama, else buat baru (jangan reuse path '#' milik grup lain).
      let groupRow = await trx('menus').where({ name: group.name, path: '#' }).first();
      if (!groupRow) {
        const [inserted] = await trx('menus')
          .insert({ ...group, parent_id: null, status: 'active' })
          .returning('*');
        groupRow = inserted;
      } else {
        await trx('menus').where({ id: groupRow.id }).update({
          icon: group.icon,
          sort_order: group.sort_order,
          parent_id: null,
          status: 'active',
        });
      }
      const groupId = groupRow.id as number;
      allMenuIds.push(groupId);

      for (const item of items) {
        const existing = await trx('menus').where({ path: item.path }).first();
        if (existing) {
          await trx('menus').where({ id: existing.id }).update({
            name: item.name,
            icon: item.icon,
            sort_order: item.sort_order,
            parent_id: groupId,
            status: 'active',
          });
          allMenuIds.push(existing.id as number);
        } else {
          const [inserted] = await trx('menus')
            .insert({ ...item, parent_id: groupId, status: 'active' })
            .returning('*');
          allMenuIds.push(inserted.id as number);
        }
      }
    }

    // Assign grup + item ke role ADMIN & SUPER_ADMIN.
    const adminRoles = await trx('roles').whereIn('code', ['ADMIN', 'SUPER_ADMIN']).select('id');
    const links: Array<{ role_id: number; menu_id: number }> = [];
    for (const r of adminRoles) {
      for (const menuId of allMenuIds) {
        links.push({ role_id: r.id, menu_id: menuId });
      }
    }
    if (links.length > 0) {
      await trx('role_menus').insert(links).onConflict(['role_id', 'menu_id']).ignore();
    }
  });
}
