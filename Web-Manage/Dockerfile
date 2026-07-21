# Multi-stage build: Angular 17 admin → nginx static

FROM node:20-bookworm AS build
WORKDIR /app

ENV NODE_OPTIONS=--max-old-space-size=8192

COPY package.json package-lock.json* ./
RUN npm install --legacy-peer-deps

COPY . .
RUN npx ng build --configuration=production

# Angular application builder output
FROM nginx:1.27-alpine AS runtime
COPY docker/nginx-spa.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist/preview/browser /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
