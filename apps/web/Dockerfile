FROM node:24-alpine AS build
WORKDIR /workspace
COPY package.json package-lock.json ./
COPY apps/web/package.json apps/web/package.json
RUN npm ci
COPY apps/web apps/web
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL NEXT_TELEMETRY_DISABLED=1
RUN npm run build --workspace @teamnav/web

FROM node:24-alpine AS runtime
WORKDIR /workspace
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1
COPY --from=build /workspace/package.json /workspace/package-lock.json ./
COPY --from=build /workspace/node_modules ./node_modules
COPY --from=build /workspace/apps/web ./apps/web
EXPOSE 3000
CMD ["npm", "run", "start", "--workspace", "@teamnav/web"]
