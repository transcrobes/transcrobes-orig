# vim:set ft=dockerfile
FROM bitnami/nginx:latest

COPY ./build/static/ /var/www/static
COPY ./images/static/location.conf /opt/bitnami/nginx/conf/bitnami/transcrobes-static.conf
