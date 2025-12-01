# ---------- Stage 1: build frontend ----------
FROM node:20-alpine AS build
WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

ARG API_BASE
ENV API_BASE=$API_BASE

RUN npm run build   # tạo /app/dist


# ---------- Stage 2: runtime nginx ----------
FROM nginx:alpine AS runtime

# dist FE sẽ nằm ở /usr/share/nginx/html
WORKDIR /usr/share/nginx/html

# copy output đã build
COPY --from=build /app/dist . 

# 🔹 COPY file cấu hình Nginx cho SPA
COPY nginx.conf /etc/nginx/conf.d/default.conf

# copy script entrypoint để generate env.js lúc container START
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 80

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
