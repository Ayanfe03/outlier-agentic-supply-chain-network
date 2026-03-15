FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

EXPOSE 8080

CMD ["sh", "-c", "printf \"window.RUNTIME_CONFIG = { VITE_REGISTRY_URL: '%s', VITE_BUYER_URL: '%s' };\" \"${VITE_REGISTRY_URL}\" \"${VITE_BUYER_URL}\" > /app/dist/runtime-config.js && npm run preview -- --host 0.0.0.0 --port ${PORT:-8080}"]
