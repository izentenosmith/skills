FROM node:22-slim
ARG ENV=dev
WORKDIR /app
COPY package.json ./
RUN npm install --omit=dev
COPY src ./src
COPY config/${ENV}.json ./config.json
ENV APP_ENV=${ENV}
USER node
CMD ["node", "src/server.js"]
