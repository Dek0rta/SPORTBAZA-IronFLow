# ── Stage 1: Build ────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm install --prefer-offline

COPY . .

ARG VITE_API_URL=https://sportbaza-ironflow-production.up.railway.app
ENV VITE_API_URL=$VITE_API_URL

# Форсируем чистую сборку без кеша Vite
RUN npx vite build --force

# ── Stage 2: Serve ────────────────────────────────────────────────────────────
FROM nginx:1.27-alpine

# envsubst нужен для подстановки $PORT в nginx.conf
RUN apk add --no-cache gettext

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/templates/default.conf.template

# Railway инжектит PORT, дефолт 80 для локального запуска
ENV PORT=80

EXPOSE ${PORT}

CMD ["sh", "-c", "envsubst '${PORT}' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"]
