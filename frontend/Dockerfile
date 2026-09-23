# ---------- Stage 1: build frontend ----------
FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm install --no-audit --no-fund

COPY . .

RUN npm run build


# ---------- Stage 2: non-root runtime nginx ----------
FROM nginxinc/nginx-unprivileged:stable-alpine AS runtime

WORKDIR /usr/share/nginx/html

# Copy frontend build
COPY --chown=nginx:nginx --from=build /app/dist .

# Nginx config
COPY --chown=nginx:nginx nginx.conf /etc/nginx/conf.d/default.conf

# Runtime entrypoint
COPY --chmod=755 --chown=nginx:nginx docker-entrypoint.sh /docker-entrypoint.sh

# Create env.js beforehand and give nginx permission to modify it
USER root

RUN touch /usr/share/nginx/html/env.js \
    && chown nginx:nginx /usr/share/nginx/html/env.js

USER nginx

EXPOSE 8080

ENTRYPOINT ["/docker-entrypoint.sh"]

CMD ["nginx", "-g", "daemon off;"]