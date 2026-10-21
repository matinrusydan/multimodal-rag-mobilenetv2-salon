import { env } from '../config/env';
import { requestAi } from './aiProxy';

/** Forward validated public chat JSON to FastAPI /ai/chat. */
export async function aiChat(body: Record<string, unknown>): Promise<object> {
  return requestAi(
    '/chat',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    },
    90_000,
  );
}

/** Forward the server-verified RBAC context to FastAPI /ai/agent. */
export async function aiAgent(
  body: Record<string, unknown>,
  auth: { userId: number; name: string; permissions: string[]; type: number },
): Promise<object> {
  return requestAi(
    '/agent',
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Internal-Token': env.AI_INTERNAL_TOKEN,
      },
      body: JSON.stringify({
        ...body,
        auth: { userId: auth.userId, name: auth.name, permissions: auth.permissions, type: auth.type },
      }),
    },
    60_000,
  );
}
