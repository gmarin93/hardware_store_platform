# syntax=docker/dockerfile:1
# Local web image. Build context: repository root (npm workspaces, single lockfile).
ARG NODE_IMAGE=node:24.22.1-alpine3.24@sha256:06d7adf3e0ef61a13f1d28682726366f97a15aa1888c934d3ecec86c33918b53

FROM ${NODE_IMAGE} AS deps
ENV NEXT_TELEMETRY_DISABLED=1 npm_config_update_notifier=false npm_config_fund=false npm_config_audit=false
WORKDIR /workspace
COPY package.json package-lock.json ./
COPY apps/web/package.json apps/web/
COPY packages/api-client/package.json packages/api-client/
COPY tests/e2e/package.json tests/e2e/
RUN npm ci

FROM deps AS build
COPY apps/web apps/web
COPY packages/api-client packages/api-client
RUN npm run build --workspace apps/web

FROM ${NODE_IMAGE} AS runtime
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 HOSTNAME=0.0.0.0 PORT=3000
WORKDIR /srv
COPY --from=build --chown=node:node /workspace/apps/web/.next/standalone ./
COPY --from=build --chown=node:node /workspace/apps/web/.next/static ./apps/web/.next/static
USER node
EXPOSE 3000
CMD ["node", "apps/web/server.js"]
