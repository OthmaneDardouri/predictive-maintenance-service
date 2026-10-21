# syntax=docker/dockerfile:1

# ---- Build stage: type-check and bundle the TypeScript app ----
FROM node:24.22.1-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# ---- Runtime stage: nginx serving static files, running as non-root on 8080 ----
FROM nginxinc/nginx-unprivileged:1.30.0-alpine
ENV API_UPSTREAM=http://api:8000
COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 8080
