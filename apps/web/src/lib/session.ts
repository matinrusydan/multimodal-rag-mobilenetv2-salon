import { type IronSession, getIronSession } from 'iron-session';
import { cookies } from 'next/headers';
import { SESSION_NAME } from './constants';

const sessionOptions = {
  cookieName: SESSION_NAME,
  password: process.env.SESSION_SECRET ?? 'change-me-session-secret',
  cookieOptions: {
    secure: process.env.NODE_ENV === 'production',
    httpOnly: true,
    sameSite: 'lax',
  },
} as const;

export interface AppSessionData {
  userId?: number;
  name?: string;
  email?: string;
  roles?: string[];
  permissions?: string[];
}

export type AppSession = IronSession<AppSessionData>;

export async function getSession(): Promise<AppSession> {
  return getIronSession<AppSessionData>(await cookies(), sessionOptions);
}
