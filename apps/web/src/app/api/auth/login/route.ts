import type { NextRequest } from 'next/server';

import { backendRequest, problem, routeError, routeOk } from '@/lib/backend';
import { mapSessionUser, setSession } from '@/lib/web-session';

type UserResponse = {
  id: number;
  name: string;
  email: string;
  type: number;
  permissions: string[];
  roles: Array<{ code: string }>;
};

type LoginData = {
  token: string;
  user: UserResponse;
};

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as { email?: string; password?: string };
    if (!body.email || !body.password) {
      return routeError(
        problem(400, 'Permintaan tidak valid', 'Email dan kata sandi wajib diisi.'),
      );
    }

    const data = await backendRequest<LoginData>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email: body.email, password: body.password }),
    });

    const user = mapSessionUser(data.user);
    await setSession({ token: data.token, user });
    return routeOk({ user });
  } catch (error) {
    return routeError(error);
  }
}
