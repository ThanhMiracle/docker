# ---------- Stage 1: build frontend ----------
FROM node:20-alpine AS build
WORKDIR /app

COPY package*.json ./
RUN npm install --no-audit --no-fund

COPY . .

ARG API_BASE
ENV API_BASE=$API_BASE

RUN npm run build   # tạo /app/dist


# ---------- Stage 2: non-root runtime nginx ----------
FROM nginxinc/nginx-unprivileged:stable-alpine AS runtime

# dist FE sẽ nằm ở /usr/share/nginx/html
WORKDIR /usr/share/nginx/html

# copy output đã build
COPY --chown=nginx:nginx --from=build /app/dist .

# 🔹 COPY file cấu hình Nginx cho SPA
COPY --chown=nginx:nginx nginx.conf /etc/nginx/conf.d/default.conf

# copy script entrypoint để generate env.js lúc container START
COPY --chmod=755 --chown=nginx:nginx docker-entrypoint.sh /docker-entrypoint.sh

USER nginx

EXPOSE 8080

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
