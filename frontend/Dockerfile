# ---------- Stage 1: build frontend ----------
FROM node:20-alpine AS build
WORKDIR /app

# cài deps
COPY package*.json ./
# nếu bạn đang dùng npm ci với lockfile thì:
# RUN npm ci
# còn nếu lockfile được tạo bên trong image thì bạn có thể đang dùng:
RUN npm install

# copy source code
COPY . .

# (tùy) cho phép build-time fallback, để dev local vẫn dùng import.meta.env.VITE_API_BASE
# Nếu bạn không cần fallback này nữa thì có thể bỏ ARG/ENV dưới đây
ARG VITE_API_BASE
ENV VITE_API_BASE=$VITE_API_BASE

# build ra dist/
RUN npm run build


# ---------- Stage 2: runtime nginx ----------
FROM nginx:alpine AS runtime
WORKDIR /usr/share/nginx/html

# copy output đã build
COPY --from=build /app/dist . 

# copy script entrypoint để generate env.js lúc container START
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# expose cổng web
EXPOSE 80

# dùng entrypoint custom -> tạo env.js từ biến môi trường runtime rồi chạy nginx
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
