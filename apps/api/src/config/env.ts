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
  OPENAI_API_KEY: z.string().optional(),
  OPENAI_MODEL: z.string().default('gpt-4o-mini'),
  OPENAI_EMBEDDING_MODEL: z.string().default('text-embedding-3-small'),
  CHROMA_PERSIST_DIR: z.string().default('./chroma_db'),
  RAG_TOP_K: z.coerce.number().default(5),
  MODEL_LENGTH_PATH: z.string().default('./cv/weights/hair_length.onnx'),
  MODEL_TYPE_PATH: z.string().default('./cv/weights/hair_type.onnx'),
  CONFIDENCE_THRESHOLD: z.coerce.number().default(0.5),
  SECURITY_ENFORCE_ENABLED: z
    .enum(['true', 'false'])
    .default('true')
    .transform((v) => v === 'true'),
  CORS_ORIGIN: z.string().default('http://localhost:3000'),
});

const parsed = EnvSchema.safeParse(process.env);

if (!parsed.success) {
  console.error('Environment tidak valid:', parsed.error.flatten().fieldErrors);
  throw new Error('Validasi environment gagal. Periksa apps/api/.env');
}

export const env = parsed.data;
