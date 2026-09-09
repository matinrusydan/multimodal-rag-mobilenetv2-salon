import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'node',
    include: ['tests/**/*.test.ts'],
    env: {
      NODE_ENV: 'test',
      PORT: '4000',
      HOST: '127.0.0.1',
      DATABASE_URL: 'postgresql://postgres:password@127.0.0.1:5432/rag_salon',
      JWT_SECRET: 'test-secret',
      SECURITY_ENFORCE_ENABLED: 'false',
    },
  },
});
