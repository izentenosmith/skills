FROM node:latest

WORKDIR /app

COPY . .

RUN npm install -g pnpm && pnpm install
RUN pnpm build

ENV NODE_ENV=production
ENV PDF_RENDER_API_KEY=eval-fake-pdfrender-key-0042

EXPOSE 3000

HEALTHCHECK CMD curl -f http://localhost:3000/health || exit 1

CMD pnpm start
