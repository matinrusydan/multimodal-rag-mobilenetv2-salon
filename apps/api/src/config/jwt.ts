import jwt from 'jsonwebtoken';
import { env } from './env';

interface JwtPayload {
  userId: number;
  name: string;
  email: string;
  type: number;
}

export function signToken(payload: JwtPayload): string {
  return jwt.sign(
    { sub: String(payload.userId), name: payload.name, email: payload.email, type: payload.type },
    env.JWT_SECRET,
    { expiresIn: env.JWT_EXPIRES_IN as jwt.SignOptions['expiresIn'] },
  );
}

export function verifyToken(token: string): { userId: number } {
  const decoded = jwt.verify(token, env.JWT_SECRET);
  const sub = typeof decoded === 'object' ? decoded.sub : undefined;
  const userId = Number(sub);
  if (!Number.isInteger(userId) || userId <= 0) {
    throw new Error('Token tidak valid');
  }
  return { userId };
}
