FROM node:22.17.0-alpine AS dependencies
WORKDIR /app
COPY package.json package-lock.json ./
COPY apps/web/package.json ./apps/web/package.json
COPY packages/api-client/package.json ./packages/api-client/package.json
RUN npm ci

FROM node:22.17.0-alpine AS build
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1 \
    API_INTERNAL_URL=http://api:8000
COPY --from=dependencies /app/node_modules ./node_modules
COPY package.json package-lock.json ./
COPY apps/web ./apps/web
COPY packages/api-client ./packages/api-client
RUN npm run build --workspace @evalpulse/web

FROM node:22.17.0-alpine AS runtime
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0
WORKDIR /app
RUN addgroup --system --gid 10001 evalpulse \
    && adduser --system --uid 10001 --ingroup evalpulse evalpulse
COPY --from=build --chown=evalpulse:evalpulse /app/apps/web/.next/standalone ./
COPY --from=build --chown=evalpulse:evalpulse /app/apps/web/.next/static ./apps/web/.next/static
USER 10001:10001
EXPOSE 3000
CMD ["node", "apps/web/server.js"]

