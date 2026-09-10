import { getIronSession } from 'iron-session';
import { cookies } from 'next/headers';

export interface SessionUser {
  id: number;
  name: string;
  email: string;
  type: number;
  permissions: string[];
  roles: string[];
}

export interface SessionData {
  token?: string;
  user?: SessionUser;
}

export const SESSION_COOKIE = 'tien_session';

const SESSION_OPTIONS = {
  cookieName: SESSION_COOKIE,
  password: process.env.SESSION_SECRET ?? 'tien-salon-dev-session-secret-2026-32chars-min',
  cookieOptions: {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax' as const,
    path: '/',
  },
};

export async function getSession(): Promise<SessionData | null> {
  const cookieStore = await cookies();
  const session = await getIronSession<SessionData>(cookieStore, SESSION_OPTIONS);
  if (!session.token || !session.user) {
    return null;
  }
  return { token: session.token, user: session.user };
}

export async function setSession(data: SessionData): Promise<void> {
  const cookieStore = await cookies();
  const session = await getIronSession<SessionData>(cookieStore, SESSION_OPTIONS);
  session.token = data.token;
  session.user = data.user;
  await session.save();
}

export async function clearSession(): Promise<void> {
  const cookieStore = await cookies();
  const session = await getIronSession<SessionData>(cookieStore, SESSION_OPTIONS);
  session.destroy();
}

export function mapSessionUser(user: {
  id: number;
  name: string;
  email: string;
  type: number;
  permissions: string[];
  roles: Array<{ code: string }>;
}): SessionUser {
  return {
    id: user.id,
    name: user.name,
    email: user.email,
    type: user.type,
    permissions: user.permissions,
    roles: user.roles.map((role) => role.code),
  };
}
