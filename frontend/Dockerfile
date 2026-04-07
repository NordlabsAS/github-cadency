# Stage 1: Build
FROM node:22-slim AS build
RUN corepack enable && corepack prepare pnpm@latest --activate
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .

ARG DEVPULSE_VERSION=0.0.0
ARG DEVPULSE_BUILD_NUMBER=0
ARG DEVPULSE_COMMIT_SHA=unknown
ARG DEVPULSE_DEPLOY_TIME=unknown

ENV VITE_DEVPULSE_VERSION=$DEVPULSE_VERSION
ENV VITE_DEVPULSE_BUILD_NUMBER=$DEVPULSE_BUILD_NUMBER
ENV VITE_DEVPULSE_COMMIT_SHA=$DEVPULSE_COMMIT_SHA
ENV VITE_DEVPULSE_DEPLOY_TIME=$DEVPULSE_DEPLOY_TIME

RUN pnpm vite build

# Stage 2: Serve
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 5173
