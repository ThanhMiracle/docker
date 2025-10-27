# Stage 1: build ứng dụng Vite/React
FROM node:20-alpine AS build
WORKDIR /app

# 1. Cài deps
COPY package*.json ./
RUN npm install

# 2. Copy source code
COPY . .

# 3. Nhận biến từ docker-compose build args
#    docker-compose.yaml sẽ truyền args:
#    build:
#      args:
#        VITE_API_BASE: "http://api.example.com"
ARG VITE_API_BASE
ENV VITE_API_BASE=$VITE_API_BASE

# 4. Build ra thư mục dist (Vite sẽ embed import.meta.env.VITE_API_BASE)
RUN npm run build


# Stage 2: chạy Nginx để serve static
FROM nginx:alpine AS runtime
WORKDIR /usr/share/nginx/html

# Copy build output (static files) sang Nginx document root
COPY --from=build /app/dist . 

# Dùng nginx default config
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
