import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'node',
    include: ['tests/**/*.test.ts'],
    fileParallelism: false,
    hookTimeout: 30_000,
    testTimeout: 20_000,
    env: {
      NODE_ENV: 'test',
      PORT: '4000',
      HOST: '127.0.0.1',
    },
  },
});
