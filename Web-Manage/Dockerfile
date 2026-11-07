# Multi-stage build: Angular 17 admin → nginx static

FROM node:20-bookworm AS build
WORKDIR /app

ENV NODE_OPTIONS=--max-old-space-size=8192

COPY package.json package-lock.json* ./
RUN npm install --legacy-peer-deps

COPY . .
# assets/config.json is git-ignored; ship the placeholder so the asset exists. The runtime
# entrypoint overwrites it from GOOGLE_MAPS_API_KEY / GOOGLE_MAPS_MAP_ID on container start.
RUN [ -f src/assets/config.json ] || cp src/assets/config.example.json src/assets/config.json
RUN npx ng build --configuration=production

# Angular application builder output
FROM nginx:1.27-alpine AS runtime
COPY docker/nginx-spa.conf /etc/nginx/conf.d/default.conf
COPY docker/40-runtime-config.sh /docker-entrypoint.d/40-runtime-config.sh
RUN chmod +x /docker-entrypoint.d/40-runtime-config.sh
COPY --from=build /app/dist/preview/browser /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
