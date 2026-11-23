# syntax=docker/dockerfile:1
FROM node:22-slim AS runtime
WORKDIR /app
COPY package.json ./
RUN npm install --omit=dev
COPY src ./src
USER node
EXPOSE 3000
CMD ["node", "src/server.js"]
