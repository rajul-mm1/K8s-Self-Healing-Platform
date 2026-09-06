# ---- build stage ----
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json ./
RUN npm install --omit=dev
COPY . .

# ---- runtime stage ----
FROM node:20-alpine
WORKDIR /app
RUN addgroup -S app && adduser -S app -G app
COPY --from=build /app /app
USER app
ENV NODE_ENV=production
EXPOSE 5000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD wget -qO- http://localhost:5000/health || exit 1
CMD ["node", "server.js"]
