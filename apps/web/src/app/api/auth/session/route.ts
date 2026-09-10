import { problem, routeError, routeOk } from '@/lib/backend';
import { getSession } from '@/lib/web-session';

export async function GET() {
  const session = await getSession();
  if (!session) {
    return routeError(problem(401, 'Tidak terautentikasi', 'Silakan masuk terlebih dahulu.'));
  }
  return routeOk({ user: session.user });
}
