FROM node:22-alpine AS frontend-builder

WORKDIR /build

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/public ./public
COPY frontend/scripts ./scripts
RUN node scripts/generate-icons.mjs

COPY frontend/index.html frontend/tsconfig.json frontend/tsconfig.app.json frontend/vite.config.ts ./
COPY frontend/src ./src
RUN npm run build


FROM python:3.12-slim AS backend-builder

WORKDIR /build
COPY pyproject.toml ./
COPY backend ./backend
ARG PIP_INDEX_URL=https://pypi.org/simple
RUN pip install --no-cache-dir --index-url ${PIP_INDEX_URL} .


FROM python:3.12-slim AS runtime

COPY --from=backend-builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=backend-builder /usr/local/bin /usr/local/bin

WORKDIR /app
COPY backend ./backend
COPY alembic.ini ./
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

COPY --from=frontend-builder /build/dist /app/static

ENV SHRED_DATABASE_URL=sqlite:////data/shred.db

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
