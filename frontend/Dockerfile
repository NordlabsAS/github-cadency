FROM node:22-slim

RUN corepack enable && corepack prepare pnpm@latest --activate

WORKDIR /app

COPY package.json pnpm-lock.yaml ./
RUN pnpm install --no-frozen-lockfile

COPY . .

CMD ["sh", "-c", "pnpm install --no-frozen-lockfile && pnpm dev --host"]
