# Stage 1: build ứng dụng Vite/React
FROM node:20-alpine AS build
WORKDIR /app

# cài deps
COPY package*.json ./
RUN npm install

# copy source
COPY . .

# build ra thư mục dist/
RUN npm run build

# Stage 2: chạy Nginx để serve static
FROM nginx:alpine AS runtime
WORKDIR /usr/share/nginx/html

# copy build output vào nginx document root
COPY --from=build /app/dist . 

# copy env template và đặt tên env.js (sẽ bị patch lúc container start)
COPY public/env.template.js ./env.js

# entrypoint script để inject biến môi trường khi container khởi động
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# (tuỳ bạn) nếu SPA cần luôn trả index.html cho mọi route, bạn có thể thêm nginx.conf custom.
# Ví dụ: uncomment nếu bạn có file cấu hình tùy chỉnh
# COPY nginx.conf /etc/nginx/conf.d/default.conf

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
