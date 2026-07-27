FROM node:24-alpine AS dependencies
WORKDIR /workspace
COPY package.json package-lock.json ./
COPY apps/web/package.json apps/web/package.json
RUN npm ci

FROM dependencies AS build
COPY apps/web apps/web
ARG NEXT_PUBLIC_API_URL=
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL NEXT_TELEMETRY_DISABLED=1
RUN npm run build --workspace @teamnav/web
RUN rm -rf /workspace/apps/web/.next/standalone/node_modules/sharp \
    /workspace/apps/web/.next/standalone/node_modules/@img

FROM node:24-alpine AS runtime
RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs
WORKDIR /workspace/apps/web
ENV HOSTNAME=0.0.0.0 NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3000
COPY --from=build --chown=nextjs:nodejs /workspace/apps/web/.next/standalone /workspace
COPY --from=build --chown=nextjs:nodejs /workspace/apps/web/.next/static ./.next/static
USER nextjs
EXPOSE 3000
CMD ["node", "server.js"]
