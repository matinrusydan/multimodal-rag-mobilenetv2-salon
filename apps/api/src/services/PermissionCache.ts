const TTL_MS = 60_000;

interface CacheEntry {
  permissions: string[];
  expiresAt: number;
}

export class PermissionCache {
  private readonly store = new Map<number, CacheEntry>();

  get(userId: number): string[] | undefined {
    const entry = this.store.get(userId);
    if (!entry) return undefined;
    if (Date.now() > entry.expiresAt) {
      this.store.delete(userId);
      return undefined;
    }
    return entry.permissions;
  }

  set(userId: number, permissions: string[]): void {
    this.store.set(userId, { permissions, expiresAt: Date.now() + TTL_MS });
  }

  invalidate(userId: number): void {
    this.store.delete(userId);
  }
}

export const permissionCache = new PermissionCache();
