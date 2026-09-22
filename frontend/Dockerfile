FROM node:22-slim AS base

WORKDIR /app

COPY package.json ./
RUN npm install

FROM base AS dev

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

FROM base AS build

COPY . .
RUN npm run build

FROM nginx:1.27-alpine AS prod

COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
