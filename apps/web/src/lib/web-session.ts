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

const DEV_SESSION_SECRET = 'tien-salon-dev-session-secret-2026-32chars-min';

export function sessionPassword(
  secret: string | undefined,
  environment: string | undefined,
): string {
  const value = secret?.trim();
  if (
    environment === 'production' &&
    (!value ||
      value.length < 32 ||
      value === DEV_SESSION_SECRET ||
      /^(change[-_ ]?me|dev(?:elopment)?[-_ ]|example[-_ ]|your[-_ ])/i.test(value))
  ) {
    throw new Error('SESSION_SECRET wajib diisi minimal 32 karakter dan bukan secret bawaan.');
  }
  return secret ?? DEV_SESSION_SECRET;
}

function sessionOptions() {
  return {
    cookieName: SESSION_COOKIE,
    password: sessionPassword(process.env.SESSION_SECRET, process.env.NODE_ENV),
    cookieOptions: {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax' as const,
      path: '/',
    },
  };
}

export async function getSession(): Promise<SessionData | null> {
  const cookieStore = await cookies();
  const session = await getIronSession<SessionData>(cookieStore, sessionOptions());
  if (!session.token || !session.user) {
    return null;
  }
  return { token: session.token, user: session.user };
}

export async function setSession(data: SessionData): Promise<void> {
  const cookieStore = await cookies();
  const session = await getIronSession<SessionData>(cookieStore, sessionOptions());
  session.token = data.token;
  session.user = data.user;
  await session.save();
}

export async function clearSession(): Promise<void> {
  const cookieStore = await cookies();
  const session = await getIronSession<SessionData>(cookieStore, sessionOptions());
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
