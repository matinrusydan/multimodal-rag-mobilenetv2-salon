import { backendRequest, routeError, routeOk } from '@/lib/backend';

export async function GET() {
  try {
    const data = await backendRequest('/services');
    return routeOk(data);
  } catch (error) {
    return routeError(error);
  }
}
