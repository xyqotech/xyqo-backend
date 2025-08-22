FROM node:18-alpine

WORKDIR /app

# Copy minimal files
COPY package.json .
COPY server.js .

# Environment
ENV PORT=8000
ENV NODE_ENV=production

EXPOSE $PORT

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:$PORT/health || exit 1

CMD ["npm", "start"]
