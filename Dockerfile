# ---- Builder stage: build the headless openDAW host ----
# The headless host is a small standalone Vite app (andremichelle/openDAW-headless)
# that pulls @opendaw/studio-sdk from npm. It is NOT part of the openDAW
# monorepo — andremichelle/openDAW has no headless-daw directory, so cloning
# it here produced an image with no host at all (the COPY below failed).
FROM node:23-slim AS opendaw-builder

RUN apt-get update && apt-get install -y git openssl && rm -rf /var/lib/apt/lists/*

WORKDIR /build
RUN git clone --depth 1 https://github.com/andremichelle/openDAW-headless.git .

# vite.config.ts eagerly readFileSync()s localhost-key.pem / localhost.pem at
# config load — even for `vite build` — so a fresh clone fails with ENOENT.
# Generate throwaway certs (only used by the dev server we never run here).
RUN openssl req -x509 -newkey rsa:2048 -keyout localhost-key.pem \
    -out localhost.pem -days 1 -nodes -subj "/CN=localhost" 2>/dev/null

# Install deps and build the static host (outputs to /build/dist)
RUN npm install --legacy-peer-deps
RUN npm run build

# ---- Runtime stage ----
FROM python:3.12-slim AS runtime

# Chromium runtime libraries only (no Node.js needed at runtime)
RUN apt-get update && apt-get install -y \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
    libgbm1 libasound2 libpango-1.0-0 libcairo2 libgdk-pixbuf-2.0-0 \
    libnspr4 libnss3 fonts-liberation curl \
    && rm -rf /var/lib/apt/lists/*

# Copy built headless host (Vite dist output, self-contained incl. dist/wasm)
COPY --from=opendaw-builder /build/dist /opendaw/headless-daw/dist

# Copy opendaw-mcp
COPY . /app/opendaw-mcp
WORKDIR /app/opendaw-mcp

# Install Python dependencies
RUN python3 -m pip install --no-cache-dir -r requirements.txt && \
    python3 -m playwright install chromium

# Environment variables
ENV OPENDAW_HOST_DIR=/opendaw/headless-daw
ENV OPENDAW_URL=http://localhost:5174
ENV OPENDAW_EXPORT_DIR=/app/exports
ENV OPENDAW_SERVE_MODE=static
ENV OPENDAW_STATIC_DIR=/opendaw/headless-daw/dist

# Create exports directory
RUN mkdir -p /app/exports

LABEL io.modelcontextprotocol.server.name="io.github.ameobius-ai/opendaw-mcp"

EXPOSE 8080

# Start static server and MCP server
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
