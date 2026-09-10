import { routeOk } from '@/lib/backend';
import { clearSession } from '@/lib/web-session';

export async function POST() {
  await clearSession();
  return routeOk({});
}
