FROM node:23-slim AS opendaw-builder

# Build openDAW from source
RUN apt-get update && apt-get install -y git python3 make g++ && rm -rf /var/lib/apt/lists/*

WORKDIR /build
RUN git clone --depth 1 https://github.com/andremichelle/openDAW.git .

# Install deps and build
RUN npm install --legacy-peer-deps
RUN npm run build

# Runtime stage
FROM python:3.12-slim AS runtime

# Install Python dependencies only (no Node.js needed)
RUN apt-get update && apt-get install -y \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
    libgbm1 libasound2 libpango-1.0-0 libcairo2 libgdk-pixbuf-2.0-0 \
    libnspr4 libnss3 fonts-liberation curl \
    && rm -rf /var/lib/apt/lists/*

# Copy built openDAW (only dist folder)
COPY --from=opendaw-builder /build/headless-daw/dist /opendaw/headless-daw/dist

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

LABEL io.modelcontextprotocol.server.name="io.github.AMEOBIUS/opendaw-mcp"

EXPOSE 8080

# Start static server and MCP server
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
