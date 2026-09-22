FROM nginxinc/nginx-unprivileged:stable-alpine

COPY --chown=nginx:nginx nginx.conf /etc/nginx/nginx.conf

USER nginx

EXPOSE 8080
