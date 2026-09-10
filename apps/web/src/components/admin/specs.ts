import type { FieldSpec, ResourceSpec } from '@/components/admin/resource-manager';

const roleTypeOptions = [
  { value: '1', label: 'Reguler' },
  { value: '0', label: 'Super' },
];

const statusOptions = [
  { value: 'active', label: 'Aktif' },
  { value: 'inactive', label: 'Nonaktif' },
];

const methodOptions = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'].map((method) => ({
  value: method,
  label: method,
}));

function nullableId(value: unknown): number | null | undefined {
  if (value === '' || value === null || value === undefined) return null;
  return Number(value);
}

function toNumberArray(value: unknown): number[] {
  if (!Array.isArray(value)) return [];
  return value.map((item) => Number(item)).filter((item) => Number.isFinite(item) && item > 0);
}

const usersFields: FieldSpec[] = [
  { key: 'name', label: 'Nama', type: 'text', required: true },
  { key: 'email', label: 'Email', type: 'email', required: true },
  {
    key: 'password',
    label: 'Password (min. 8 karakter)',
    type: 'password',
    required: true,
    minLength: 8,
    createOnly: true,
  },
  { key: 'type', label: 'Tipe', type: 'select', options: roleTypeOptions },
  { key: 'status', label: 'Status', type: 'select', options: statusOptions },
  { key: 'roleIds', label: 'Assign Role', type: 'multiselect', source: 'roles' },
];

const rolesFields: FieldSpec[] = [
  { key: 'name', label: 'Nama', type: 'text', required: true },
  { key: 'code', label: 'Kode (A-Z, 0-9, _)', type: 'text', required: true },
  { key: 'type', label: 'Tipe', type: 'select', options: roleTypeOptions },
  { key: 'parentId', label: 'Parent', type: 'select', source: 'roles' },
  { key: 'description', label: 'Deskripsi', type: 'text' },
  { key: 'permissionIds', label: 'Assign Permission', type: 'multiselect', source: 'permissions' },
];

export const userResource: ResourceSpec = {
  resource: 'users',
  singular: 'User',
  columns: [
    { key: 'id', label: 'ID' },
    { key: 'name', label: 'Nama' },
    { key: 'email', label: 'Email' },
    {
      key: 'type',
      label: 'Tipe',
      render: (row) => (Number(row.type) === 0 ? 'Super Admin' : 'Reguler'),
    },
    { key: 'status', label: 'Status' },
    { key: 'roles', label: 'Role' },
  ],
  fields: usersFields,
  buildCreate: (form) => ({
    name: String(form.name ?? ''),
    email: String(form.email ?? ''),
    password: String(form.password ?? ''),
    type: form.type === '' ? undefined : Number(form.type),
  }),
  buildUpdate: (form) => {
    const body: Record<string, unknown> = {
      name: String(form.name ?? ''),
      email: String(form.email ?? ''),
      type: form.type === '' ? undefined : Number(form.type),
    };
    if (form.status) body.status = String(form.status);
    if (String(form.password ?? '').length > 0) body.password = String(form.password);
    return body;
  },
  assign: { suffix: 'roles', key: 'roleIds' },
  optionSources: [{ key: 'roles', url: '/api/admin/roles' }],
};

export const roleResource: ResourceSpec = {
  resource: 'roles',
  singular: 'Role',
  columns: [
    { key: 'id', label: 'ID' },
    { key: 'name', label: 'Nama' },
    { key: 'code', label: 'Kode' },
    { key: 'description', label: 'Deskripsi' },
    {
      key: 'type',
      label: 'Tipe',
      render: (row) => (Number(row.type) === 0 ? 'Super' : 'Reguler'),
    },
  ],
  fields: rolesFields,
  buildCreate: (form) => ({
    name: String(form.name ?? ''),
    code: String(form.code ?? ''),
    type: form.type === '' ? undefined : Number(form.type),
    parentId: nullableId(form.parentId),
    description: form.description === '' ? null : String(form.description),
  }),
  buildUpdate: (form) => ({
    name: String(form.name ?? ''),
    code: String(form.code ?? ''),
    type: form.type === '' ? undefined : Number(form.type),
    parentId: nullableId(form.parentId),
    description: form.description === '' ? null : String(form.description),
  }),
  assign: { suffix: 'permissions', key: 'permissionIds' },
  optionSources: [
    { key: 'roles', url: '/api/admin/roles' },
    { key: 'permissions', url: '/api/admin/permissions' },
  ],
};

export const permissionResource: ResourceSpec = {
  resource: 'permissions',
  singular: 'Permission',
  columns: [
    { key: 'id', label: 'ID' },
    { key: 'name', label: 'Nama' },
    { key: 'resource', label: 'Resource' },
    { key: 'description', label: 'Deskripsi' },
  ],
  fields: [
    { key: 'name', label: 'Nama (resource.action)', type: 'text', required: true },
    { key: 'resource', label: 'Resource', type: 'text', required: true },
    { key: 'description', label: 'Deskripsi', type: 'text' },
  ],
  buildCreate: (form) => ({
    name: String(form.name ?? ''),
    resource: String(form.resource ?? ''),
    description: form.description === '' ? null : String(form.description),
  }),
  buildUpdate: (form) => ({
    name: String(form.name ?? ''),
    resource: String(form.resource ?? ''),
    description: form.description === '' ? null : String(form.description),
  }),
};

export const routeResource: ResourceSpec = {
  resource: 'routes',
  singular: 'Route',
  columns: [
    { key: 'id', label: 'ID' },
    { key: 'path', label: 'Path' },
    { key: 'method', label: 'Method' },
    { key: 'name', label: 'Nama' },
  ],
  fields: [
    { key: 'path', label: 'Path (diawali /)', type: 'text', required: true },
    { key: 'name', label: 'Nama', type: 'text', required: true },
    { key: 'method', label: 'Method', type: 'select', options: methodOptions },
  ],
  buildCreate: (form) => ({
    path: String(form.path ?? ''),
    name: String(form.name ?? ''),
    method: form.method === '' ? undefined : String(form.method),
  }),
  buildUpdate: (form) => ({
    path: String(form.path ?? ''),
    name: String(form.name ?? ''),
    method: form.method === '' ? undefined : String(form.method),
  }),
};

export const menuResource: ResourceSpec = {
  resource: 'menus',
  singular: 'Menu',
  columns: [
    { key: 'id', label: 'ID' },
    { key: 'name', label: 'Nama' },
    { key: 'path', label: 'Path' },
    { key: 'icon', label: 'Ikon' },
    { key: 'sortOrder', label: 'Urutan' },
  ],
  fields: [
    { key: 'name', label: 'Nama', type: 'text', required: true },
    { key: 'path', label: 'Path (diawali /)', type: 'text', required: true },
    { key: 'icon', label: 'Ikon', type: 'text' },
    { key: 'parentId', label: 'Parent', type: 'select', source: 'menus' },
    { key: 'sortOrder', label: 'Urutan', type: 'number' },
    { key: 'roleIds', label: 'Assign Role', type: 'multiselect', source: 'roles' },
  ],
  buildCreate: (form) => ({
    name: String(form.name ?? ''),
    path: String(form.path ?? ''),
    icon: form.icon === '' ? null : String(form.icon),
    parentId: nullableId(form.parentId),
    sortOrder: form.sortOrder === '' ? undefined : Number(form.sortOrder),
  }),
  buildUpdate: (form) => ({
    name: String(form.name ?? ''),
    path: String(form.path ?? ''),
    icon: form.icon === '' ? null : String(form.icon),
    parentId: nullableId(form.parentId),
    sortOrder: form.sortOrder === '' ? undefined : Number(form.sortOrder),
  }),
  assign: { suffix: 'roles', key: 'roleIds' },
  optionSources: [
    { key: 'roles', url: '/api/admin/roles' },
    { key: 'menus', url: '/api/admin/menus' },
  ],
};

export const ALL_RESOURCES: ResourceSpec[] = [
  userResource,
  roleResource,
  permissionResource,
  routeResource,
  menuResource,
];
