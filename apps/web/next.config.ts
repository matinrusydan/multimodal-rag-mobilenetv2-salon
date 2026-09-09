import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  transpilePackages: ['@rag-salon/shared-types', '@rag-salon/shared-utils'],
};

export default nextConfig;
