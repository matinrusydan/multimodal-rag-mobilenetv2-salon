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

type RegisterData = {
  token: string;
  user: UserResponse;
};

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as {
      name?: string;
      email?: string;
      password?: string;
    };
    if (!body.name || !body.email || !body.password) {
      return routeError(
        problem(400, 'Permintaan tidak valid', 'Nama, email, dan kata sandi wajib diisi.'),
      );
    }

    const data = await backendRequest<RegisterData>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({
        name: body.name,
        email: body.email,
        password: body.password,
      }),
    });

    const user = mapSessionUser(data.user);
    await setSession({ token: data.token, user });
    return routeOk({ user }, 201);
  } catch (error) {
    return routeError(error);
  }
}
