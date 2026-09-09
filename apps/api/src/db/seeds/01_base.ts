import argon2 from 'argon2';
import type { Knex } from 'knex';

const DEMO_PASSWORD = 'Password123!';

const PERMISSIONS = [
  // services
  ['services.read', 'services'],
  ['services.write', 'services'],
  // reservations
  ['reservations.create', 'reservations'],
  ['reservations.read', 'reservations'],
  ['reservations.read.own', 'reservations'],
  ['reservations.write', 'reservations'],
  // payments
  ['payments.read', 'payments'],
  ['payments.write', 'payments'],
  // users
  ['users.read', 'users'],
  ['users.write', 'users'],
  ['users.delete', 'users'],
  ['users.manage', 'users'],
  // roles
  ['roles.read', 'roles'],
  ['roles.write', 'roles'],
  ['roles.delete', 'roles'],
  ['roles.manage', 'roles'],
  // permissions
  ['permissions.read', 'permissions'],
  ['permissions.write', 'permissions'],
  ['permissions.delete', 'permissions'],
  // routes
  ['routes.read', 'routes'],
  ['routes.write', 'routes'],
  ['routes.delete', 'routes'],
  // menus
  ['menus.read', 'menus'],
  ['menus.write', 'menus'],
  ['menus.delete', 'menus'],
  ['menus.manage', 'menus'],
];

const ROLE_PERMISSION_MAP: Record<string, string[]> = {
  CUSTOMER: [
    'services.read',
    'reservations.create',
    'reservations.read.own',
    'payments.write',
    'payments.read',
  ],
  STAFF: [
    'services.read',
    'services.write',
    'reservations.create',
    'reservations.read',
    'reservations.write',
    'payments.read',
    'payments.write',
  ],
  ADMIN: PERMISSIONS.map(([name]) => name),
};

const ADMIN_ROUTES = [
  { path: '/admin/users', name: 'Kelola Pengguna', method: 'GET' },
  { path: '/admin/roles', name: 'Kelola Role', method: 'GET' },
  { path: '/admin/permissions', name: 'Kelola Permission', method: 'GET' },
  { path: '/admin/routes', name: 'Kelola Route', method: 'GET' },
  { path: '/admin/menus', name: 'Kelola Menu', method: 'GET' },
];

const MENUS = [
  { name: 'Beranda', path: '/home', icon: 'home', sort_order: 1 },
  { name: 'Layanan', path: '/services', icon: 'scissors', sort_order: 2 },
  { name: 'Konsultasi', path: '/consult', icon: 'sparkles', sort_order: 3 },
  { name: 'Reservasi Baru', path: '/reservation', icon: 'calendar', sort_order: 4 },
  { name: 'Pembayaran', path: '/payment', icon: 'wallet', sort_order: 5 },
  { name: 'Pengguna', path: '/admin/users', icon: 'users', sort_order: 10 },
  { name: 'Roles', path: '/admin/roles', icon: 'shield', sort_order: 11 },
  { name: 'Permissions', path: '/admin/permissions', icon: 'key', sort_order: 12 },
  { name: 'Routes', path: '/admin/routes', icon: 'route', sort_order: 13 },
  { name: 'Menus', path: '/admin/menus', icon: 'list', sort_order: 14 },
];

const SERVICES = [
  {
    name: 'Signature Hair Spa',
    slug: 'signature-hair-spa',
    price: 325000,
    duration_min: 90,
    description:
      'Ritual hair spa khas TIEN SALON dengan pijatan relaksasi kulit kepala, masker rambut bernutrisi, dan finishing lembut untuk mengembalikan kelembapan rambut.',
    category: 'Hair Treatment',
    image: '/images/services/creambath.png',
  },
  {
    name: 'Precision Haircut',
    slug: 'precision-haircut',
    price: 220000,
    duration_min: 60,
    description:
      'Layanan haircut dengan konsultasi singkat, shaping presisi, dan styling akhir agar potongan rambut terasa rapi, ringan, dan mudah diatur.',
    category: 'Haircut',
    image: '/images/services/haircut.png',
  },
  {
    name: 'Keratin Smooth Treatment',
    slug: 'keratin-smooth-treatment',
    price: 780000,
    duration_min: 150,
    description:
      'Perawatan keratin untuk membantu mengurangi tampilan frizz dan membuat rambut terasa lebih halus tanpa menghilangkan karakter natural rambut.',
    category: 'Smoothing',
    image: '/images/services/smoothing.png',
  },
  {
    name: 'Color Gloss Refresh',
    slug: 'color-gloss-refresh',
    price: 620000,
    duration_min: 130,
    description:
      'Layanan pewarnaan rambut untuk menyegarkan tone, menambah kilau, dan membuat warna rambut terlihat lebih hidup dengan hasil tetap elegan.',
    category: 'Hair Coloring',
    image: '/images/services/coloring.png',
  },
  {
    name: 'Scalp Detox Therapy',
    slug: 'scalp-detox-therapy',
    price: 360000,
    duration_min: 75,
    description:
      'Ritual detox kulit kepala dengan cleansing, massage, dan tonic care untuk membantu rambut terasa lebih ringan dari akar.',
    category: 'Scalp Care',
    image: '/images/services/treatment.png',
  },
  {
    name: 'Volume Blowout Styling',
    slug: 'volume-blowout-styling',
    price: 280000,
    duration_min: 55,
    description:
      'Styling rambut dengan blowout natural untuk memberi volume, movement, dan hasil akhir yang rapi tanpa terlihat berlebihan.',
    category: 'Hair Styling',
    image: '/images/services/hairstyle.png',
  },
];

export async function seed(knex: Knex): Promise<void> {
  await knex.transaction(async (trx) => {
    // permissions
    const permissionRows = await trx('permissions')
      .insert(PERMISSIONS.map(([name, resource]) => ({ name, resource })))
      .returning(['id', 'name']);
    const permissionIdByName = new Map(permissionRows.map((p) => [p.name, p.id]));

    // roles
    const roleRows = await trx('roles')
      .insert([
        { name: 'Super Admin', code: 'SUPER_ADMIN', type: 0, description: 'Akses penuh sistem' },
        { name: 'Admin', code: 'ADMIN', type: 1, description: 'Pengelola layanan & RBAC' },
        { name: 'Staff', code: 'STAFF', type: 1, description: 'Staff salon' },
        { name: 'Customer', code: 'CUSTOMER', type: 1, description: 'Pelanggan' },
      ])
      .returning(['id', 'code']);
    const roleIdByCode = new Map(roleRows.map((r) => [r.code, r.id]));

    // role_permissions (SUPER_ADMIN: semua via wildcard, cukup isi role_permissions dengan semua)
    const rolePermissions: Array<{ role_id: number; permission_id: number }> = [];
    for (const [code, names] of Object.entries(ROLE_PERMISSION_MAP)) {
      const roleId = roleIdByCode.get(code);
      if (!roleId) continue;
      for (const name of names) {
        const permissionId = permissionIdByName.get(name);
        if (permissionId) rolePermissions.push({ role_id: roleId, permission_id: permissionId });
      }
    }
    const superAdminId = roleIdByCode.get('SUPER_ADMIN');
    for (const pid of permissionIdByName.values()) {
      if (superAdminId) rolePermissions.push({ role_id: superAdminId, permission_id: pid });
    }
    await trx('role_permissions').insert(rolePermissions);

    // routes + role_routes
    const routeRows = await trx('routes').insert(ADMIN_ROUTES).returning(['id']);
    const adminRoleId = roleIdByCode.get('ADMIN');
    const routeRoleRows = routeRows.map((r) => ({ role_id: adminRoleId, route_id: r.id }));
    if (superAdminId) {
      for (const route of routeRows) {
        routeRoleRows.push({ role_id: superAdminId, route_id: route.id });
      }
    }
    await trx('role_routes').insert(routeRoleRows);

    // menus + role_menus
    const menuRows = await trx('menus').insert(MENUS).returning(['id']);
    const menuRoleRows: Array<{ role_id: number; menu_id: number }> = [];
    const customerRoleId = roleIdByCode.get('CUSTOMER');
    const staffRoleId = roleIdByCode.get('STAFF');
    MENUS.forEach((menu, idx) => {
      const menuId = menuRows[idx]?.id;
      if (!menuId) return;
      if (menu.path.startsWith('/admin')) {
        if (adminRoleId) menuRoleRows.push({ role_id: adminRoleId, menu_id: menuId });
        if (superAdminId) menuRoleRows.push({ role_id: superAdminId, menu_id: menuId });
      } else {
        if (customerRoleId) menuRoleRows.push({ role_id: customerRoleId, menu_id: menuId });
        if (staffRoleId) menuRoleRows.push({ role_id: staffRoleId, menu_id: menuId });
        if (adminRoleId) menuRoleRows.push({ role_id: adminRoleId, menu_id: menuId });
        if (superAdminId) menuRoleRows.push({ role_id: superAdminId, menu_id: menuId });
      }
    });
    await trx('role_menus').insert(menuRoleRows);

    // users
    const passwordHash = await argon2.hash(DEMO_PASSWORD, { type: argon2.argon2id });
    const userRows = await trx('users')
      .insert([
        {
          name: 'Administrator',
          email: 'admin@rag-salon.id',
          password_hash: passwordHash,
          type: 0,
        },
        { name: 'Staff Salon', email: 'staff@rag-salon.id', password_hash: passwordHash, type: 1 },
        {
          name: 'Budi Santoso',
          email: 'customer@rag-salon.id',
          password_hash: passwordHash,
          type: 1,
        },
      ])
      .returning(['id', 'email']);
    const userIdByEmail = new Map(userRows.map((u) => [u.email, u.id]));
    await trx('user_roles').insert([
      { user_id: userIdByEmail.get('admin@rag-salon.id'), role_id: superAdminId },
      { user_id: userIdByEmail.get('staff@rag-salon.id'), role_id: roleIdByCode.get('STAFF') },
      {
        user_id: userIdByEmail.get('customer@rag-salon.id'),
        role_id: roleIdByCode.get('CUSTOMER'),
      },
    ]);

    // services
    await trx('services').insert(SERVICES);
  });
}
