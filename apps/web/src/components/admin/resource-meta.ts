/**
 * Metadata resource admin (data murni tanpa fungsi).
 * Aman diimpor oleh Server Component (mis. dashboard admin), berbeda dengan
 * specs.ts yang berisi fungsi dan hanya untuk Client Component.
 */
export interface ResourceMeta {
  resource: string;
  singular: string;
  label: string;
}

export const RESOURCE_META: ResourceMeta[] = [
  { resource: 'users', singular: 'User', label: 'Pengguna' },
  { resource: 'roles', singular: 'Role', label: 'Role' },
  { resource: 'permissions', singular: 'Permission', label: 'Permission' },
  { resource: 'routes', singular: 'Route', label: 'Route' },
  { resource: 'menus', singular: 'Menu', label: 'Menu' },
];
