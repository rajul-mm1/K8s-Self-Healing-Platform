# ---- build stage ----
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

# ---- runtime stage ----
FROM nginx:1.27-alpine
RUN addgroup -S app && adduser -S app -G app \
    && sed -i 's/listen\s*80;/listen 8080;/' /etc/nginx/conf.d/default.conf || true
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh \
    && chown -R app:app /usr/share/nginx/html /var/cache/nginx /var/run \
    && touch /var/run/nginx.pid && chown app:app /var/run/nginx.pid
USER app
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --retries=3 CMD wget -qO- http://localhost:8080/healthz || exit 1
ENTRYPOINT ["/docker-entrypoint.sh"]
