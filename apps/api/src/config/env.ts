import { config } from 'dotenv';
import { z } from 'zod';

config();

const EnvSchema = z.object({
  NODE_ENV: z.enum(['development', 'test', 'production']).default('development'),
  PORT: z.coerce.number().default(4000),
  HOST: z.string().default('127.0.0.1'),
  DATABASE_URL: z.string().min(1, 'DATABASE_URL wajib diisi'),
  DB_CLIENT: z.string().default('postgres'),
  DB_POOL_MIN: z.coerce.number().default(0),
  DB_POOL_MAX: z.coerce.number().default(10),
  JWT_SECRET: z.string().min(1, 'JWT_SECRET wajib diisi'),
  JWT_EXPIRES_IN: z.string().default('1d'),
  SECURITY_ENFORCE_ENABLED: z
    .enum(['true', 'false'])
    .default('true')
    .transform((v) => v === 'true'),
  CORS_ORIGIN: z.string().default('http://localhost:3000'),
  // Hop counts require a fixed ingress topology and no direct public access to the API.
  TRUST_PROXY: z
    .enum(['false', '1', '2', '3', '4', '5'])
    .default('false')
    .transform((value) => (value === 'false' ? false : Number(value))),
  AI_URL: z.string().default('http://127.0.0.1:5000'),
  AI_INTERNAL_TOKEN: z.string().default('dev-internal-token-change-me'),
}).superRefine((value, ctx) => {
  if (value.NODE_ENV !== 'production') return;

  for (const key of ['JWT_SECRET', 'AI_INTERNAL_TOKEN'] as const) {
    const secret = value[key].trim();
    if (secret.length < 32 || /^(change[-_ ]?me|dev[-_]|your[-_])/i.test(secret)) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: [key],
        message: `${key} produksi wajib minimal 32 karakter dan bukan nilai contoh/development`,
      });
    }
  }
});

const parsed = EnvSchema.safeParse(process.env);

if (!parsed.success) {
  // Report field names only: validation diagnostics must never echo environment values.
  console.error('Environment tidak valid:', Object.keys(parsed.error.flatten().fieldErrors));
  throw new Error('Validasi environment gagal. Periksa apps/api/.env');
}

export const env = parsed.data;
