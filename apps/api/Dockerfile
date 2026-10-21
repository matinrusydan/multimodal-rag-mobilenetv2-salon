# Build from the repository root: docker build -f apps/api/Dockerfile .
FROM node:22-bookworm-slim AS base
WORKDIR /app
ENV PNPM_HOME=/pnpm
ENV PATH=$PNPM_HOME:$PATH
RUN corepack enable && corepack prepare pnpm@10.15.1 --activate
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml tsconfig.base.json ./
COPY apps/api/package.json ./apps/api/package.json
COPY packages/shared-types/package.json ./packages/shared-types/package.json
COPY packages/shared-utils/package.json ./packages/shared-utils/package.json

FROM base AS build
RUN pnpm install --filter api... --frozen-lockfile
COPY apps/api/src ./apps/api/src
COPY apps/api/tests ./apps/api/tests
COPY apps/api/tsconfig.json apps/api/knexfile.ts ./apps/api/
COPY packages/shared-types ./packages/shared-types
COPY packages/shared-utils ./packages/shared-utils
RUN pnpm --filter api typecheck

FROM base AS runtime
ENV NODE_ENV=production
ENV HOST=0.0.0.0
ENV PORT=4000
RUN pnpm install --filter api... --prod --frozen-lockfile
COPY --from=build /app/apps/api/src ./apps/api/src
COPY --from=build /app/apps/api/tsconfig.json /app/apps/api/knexfile.ts ./apps/api/
COPY --from=build /app/packages/shared-types/src ./packages/shared-types/src
COPY --from=build /app/packages/shared-utils/src ./packages/shared-utils/src
USER node
WORKDIR /app/apps/api
EXPOSE 4000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD node -e "fetch('http://127.0.0.1:'+process.env.PORT+'/api/health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"
CMD ["pnpm", "start"]
