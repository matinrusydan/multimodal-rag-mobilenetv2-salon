import type { Knex } from 'knex';

/**
 * Struktur menu admin bertingkat (mendukung 3 level).
 *
 * Aturan render sidebar:
 *  - parent BER-ICON + children  -> dropdown/accordion
 *  - parent TANPA icon + children -> judul teks + isi flat
 *  - tanpa children + icon/path   -> item tunggal (link)
 *  - tanpa children + tanpa icon  -> judul teks murni
 *
 * Idempotent: cari node by path (leaf) / by name (grup), upsert.
 */

interface MenuNode {
  name: string;
  path: string; // leaf punya path nyata; grup/judul '#'
  icon: string | null;
  children?: MenuNode[];
}

const MENUS: MenuNode[] = [
  { name: 'Dashboard', path: '/admin', icon: 'dashboard' },
  {
    name: 'Manajemen Salon',
    path: '#',
    icon: 'scissors',
    children: [
      { name: 'Layanan & Harga', path: '/admin/services', icon: 'scissors' },
    ],
  },
  {
    name: 'Transaksi',
    path: '#',
    icon: 'wallet',
    children: [
      { name: 'Reservasi', path: '/admin/reservations', icon: 'calendar' },
      { name: 'Pembayaran', path: '/payment', icon: 'wallet' },
    ],
  },
  {
    name: 'Konten & Info',
    path: '#',
    icon: 'settings',
    children: [
      { name: 'Info Salon', path: '/admin/settings', icon: 'settings' },
      { name: 'Dokumen RAG', path: '/admin/knowledge', icon: 'file' },
    ],
  },
  {
    name: 'Akses & Keamanan',
    path: '#',
    icon: null,
    children: [
      {
        name: 'Manajemen Menu',
        path: '#',
        icon: 'shield',
        children: [
          { name: 'Pengguna', path: '/admin/users', icon: 'users' },
          { name: 'Role', path: '/admin/roles', icon: 'shield' },
          { name: 'Permission', path: '/admin/permissions', icon: 'key' },
          { name: 'Routes', path: '/admin/routes', icon: 'route' },
          { name: 'Menu', path: '/admin/menus', icon: 'list' },
          { name: 'Akses Menu', path: '/admin/role-menus', icon: 'shield' },
        ],
      },
    ],
  },
];

export async function seed(knex: Knex): Promise<void> {
  await knex.transaction(async (trx) => {
    const managedIds: number[] = [];

    // Cari node: leaf by path, grup by name (path '#').
    // Bila grup by name tidak ada, coba pakai grup '#' yatim (mis. hasil rename
    // "Manajemen Admin" -> "Manajemen Menu") agar tidak membuat duplikat.
    const knownGroupNames = new Set<string>();
    const collectGroupNames = (nodes: MenuNode[]) => {
      for (const n of nodes) {
        if (n.path === '#' || (n.children && n.children.length > 0)) knownGroupNames.add(n.name);
        if (n.children) collectGroupNames(n.children);
      }
    };
    collectGroupNames(MENUS);

    async function upsertNode(node: MenuNode, parentId: number | null, sortOrder: number): Promise<number> {
      const isGroup = node.path === '#' || (node.children && node.children.length > 0);
      let row: Record<string, unknown> | undefined;
      if (isGroup) {
        row = await trx('menus').where({ name: node.name, path: '#' }).first();
        if (!row) {
          // Reuse grup '#' yatim (nama tidak dikenal) sebagai hasil rename.
          row = await trx('menus')
            .where({ path: '#' })
            .whereNotIn('name', [...knownGroupNames])
            .first();
        }
      } else {
        row = await trx('menus').where({ path: node.path }).first();
      }

      if (row) {
        await trx('menus').where({ id: row.id }).update({
          name: node.name,
          icon: node.icon,
          sort_order: sortOrder,
          parent_id: parentId,
          status: 'active',
        });
      } else {
        const [inserted] = await trx('menus')
          .insert({
            name: node.name,
            path: isGroup ? '#' : node.path,
            icon: node.icon,
            parent_id: parentId,
            sort_order: sortOrder,
            status: 'active',
          })
          .returning('*');
        row = inserted;
      }
      const id = (row as { id: number }).id;
      managedIds.push(id);

      if (node.children) {
        let order = 1;
        for (const child of node.children) {
          const childId = await upsertNode(child, id, order);
          managedIds.push(childId);
          order += 1;
        }
      }
      return id;
    }

    let topOrder = 1;
    for (const node of MENUS) {
      await upsertNode(node, null, topOrder);
      topOrder += 1;
    }

    // Non-aktifkan grup lama yang tidak lagi dikelola (path '#'): mis. sisa
    // "Menu Admin", "Akses & Keamanan" versi lama, atau grup duplikat.
    const managedNames = ['Dashboard', 'Manajemen Salon', 'Transaksi', 'Konten & Info', 'Akses & Keamanan', 'Manajemen Menu'];
    await trx('menus')
      .where({ path: '#' })
      .whereNotIn('name', managedNames)
      .update({ status: 'inactive', parent_id: null });

    // Assign menu yang dikelola ke role ADMIN & SUPER_ADMIN.
    const adminRoles = await trx('roles').whereIn('code', ['ADMIN', 'SUPER_ADMIN']).select('id');
    const links: Array<{ role_id: number; menu_id: number }> = [];
    for (const r of adminRoles) {
      for (const menuId of managedIds) {
        links.push({ role_id: r.id, menu_id: menuId });
      }
    }
    if (links.length > 0) {
      await trx('role_menus').insert(links).onConflict(['role_id', 'menu_id']).ignore();
    }
  });
}
