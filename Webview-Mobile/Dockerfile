# Multi-stage build: Angular 15 mobile → nginx static (served under /mobile/)

FROM node:18-bookworm AS build
WORKDIR /app

ENV NODE_OPTIONS=--max-old-space-size=8192

# canvas / native optional deps — skip scripts; browser build does not need them
COPY package.json package-lock.json* ./
RUN npm install --legacy-peer-deps --ignore-scripts

COPY . .
RUN npx ng build --configuration=production --base-href=/mobile/

FROM nginx:1.27-alpine AS runtime
COPY docker/nginx-spa.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
