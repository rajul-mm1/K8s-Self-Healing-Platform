#!/bin/sh
# Substitutes the API base URL into env.js at container start so the same
# built image can be reused across environments without a rebuild.
set -e
API_BASE_URL="${API_BASE_URL:-/api}"
sed "s#__API_BASE_URL__#${API_BASE_URL}#g" /usr/share/nginx/html/env-template.js > /usr/share/nginx/html/env.js
exec nginx -g 'daemon off;'
