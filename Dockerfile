FROM node:23-slim AS opendaw-builder

# Build openDAW from source
RUN apt-get update && apt-get install -y git python3 make g++ && rm -rf /var/lib/apt/lists/*

WORKDIR /build
RUN git clone --depth 1 https://github.com/andremichelle/openDAW.git .

# Install deps and build (turbo handles the monorepo)
RUN npm install --legacy-peer-deps
RUN npm run build

# ---- Runtime stage ----
FROM node:23-slim AS runtime

RUN apt-get update && apt-get install -y \
    python3 python3-pip python3-venv \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
    libgbm1 libasound2 libpango-1.0-0 libcairo2 libgdk-pixbuf-2.0-0 \
    libnspr4 libnss3 fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Copy built openDAW
WORKDIR /app
COPY --from=opendaw-builder /build /opendaw

# Clone and install opendaw-mcp
RUN git clone --depth 1 https://github.com/AMEOBIUS/opendaw-mcp.git /app/opendaw-mcp
WORKDIR /app/opendaw-mcp

RUN python3 -m venv venv && \
    venv/bin/pip install --no-cache-dir -r requirements.txt && \
    venv/bin/playwright install chromium

ENV OPENDAW_HOST_DIR=/opendaw/headless-daw
ENV OPENDAW_URL=http://localhost:5174
ENV OPENDAW_EXPORT_DIR=/app/exports
ENV NODE_BIN_DIR=/usr/local/bin
ENV HOST=0.0.0.0
ENV PORT=8080

RUN mkdir -p /app/exports

EXPOSE 8080

# Start Vite dev server for openDAW, then the MCP server
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
