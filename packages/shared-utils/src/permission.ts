/**
 * Cek apakah `required` cocok dengan permission user.
 * Mendukung wildcard: `users.read`, `users.*`, `users.manage`, `users.read.own`.
 */
export function hasPermission(userPermissions: string[], required: string, own = false): boolean {
  if (!required) return true;

  for (const p of userPermissions) {
    if (p === required) return true;
    if (p === '*') return true;
    if (p.endsWith('.*')) {
      const prefix = p.slice(0, -2);
      if (required.startsWith(`${prefix}.`)) return true;
    }
    if (p.endsWith('.manage')) {
      const prefix = p.slice(0, -'.manage'.length);
      if (required.startsWith(`${prefix}.`)) return true;
    }
  }

  // kepemilikan
  if (own) {
    const ownRequired = `${required}.own`;
    for (const p of userPermissions) {
      if (p === ownRequired) return true;
    }
  }

  return false;
}

/** Cek wildcard sederhana: `users.read` vs `users.read`, `users.*` */
export function matchPermission(userPermission: string, required: string): boolean {
  if (userPermission === required) return true;
  if (userPermission === '*') return true;
  if (userPermission.endsWith('.*')) {
    return required.startsWith(`${userPermission.slice(0, -1)}`);
  }
  return false;
}
