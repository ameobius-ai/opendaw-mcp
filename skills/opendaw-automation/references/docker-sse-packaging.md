# Docker + SSE Transport Packaging

Added 2026-07-03. Enables remote deployment and Glama.ai introspection.

## Files created

### Dockerfile (multi-stage)

```dockerfile
FROM node:23-slim AS opendaw-builder
RUN apt-get update && apt-get install -y git python3 make g++ && rm -rf /var/lib/apt/lists/*
WORKDIR /build
RUN git clone --depth 1 https://github.com/andremichelle/openDAW.git .
RUN npm install --legacy-peer-deps
RUN npm run build

FROM node:23-slim AS runtime
RUN apt-get update && apt-get install -y \
    python3 python3-pip python3-venv \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
    libgbm1 libasound2 libpango-1.0-0 libcairo2 libgdk-pixbuf-2.0-0 \
    libnspr4 libnss3 fonts-liberation \
    && rm -rf /var/lib/apt/lists/*
COPY --from=opendaw-builder /build /opendaw
WORKDIR /app
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
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
```

### entrypoint.sh

```bash
#!/bin/bash
set -e
cd /opendaw/headless-daw
node node_modules/vite/bin/vite.js --port 5174 --host 0.0.0.0 &
VITE_PID=$!
echo "Waiting for Vite dev server..."
for i in $(seq 1 30); do
    if curl -s http://localhost:5174 > /dev/null 2>&1; then
        echo "Vite is ready"
        break
    fi
    sleep 1
done
cd /app/opendaw-mcp
export MCP_TRANSPORT=sse
export FASTMCP_HOST=0.0.0.0
export FASTMCP_PORT=8080
exec venv/bin/python server.py
```

### .dockerignore

```
venv/
__pycache__/
*.pyc
.git/
.worktrees/
exports/
test_*.py
```

## Key decisions

1. **Multi-stage build** — openDAW built from source in builder stage, copied to runtime. Keeps image smaller.
2. **node:23-slim base** — openDAW requires Node 23. slim variant saves space.
3. **Chromium deps** — Playwright needs libnss3, libgbm, libasound2, etc. Full list from Playwright docs.
4. **SSE mode in Docker** — `MCP_TRANSPORT=sse` + `FASTMCP_HOST=0.0.0.0` for external access. Glama introspection hits `http://host:8080/sse`.
5. **Vite --host 0.0.0.0** — needed inside Docker so the MCP server can reach it.
6. **curl wait loop** — entrypoint waits up to 30s for Vite before starting MCP.

## FastMCP SSE internals

FastMCP `run(transport='sse')` calls `run_sse_async()` which:
1. Creates a Starlette app via `self.sse_app(mount_path)`
2. Creates a uvicorn Config from `self.settings.host` / `self.settings.port`
3. Starts the server

Settings are read from env vars:
- `FASTMCP_HOST` (default `127.0.0.1`)
- `FASTMCP_PORT` (default `8000`)

**Do NOT pass host/port to `mcp.run()`** — signature is `run(transport, mount_path)` only.

## requirements.txt

Must include `uvicorn>=0.20` — SSE transport imports it lazily. Without uvicorn, `mcp.run(transport='sse')` fails with ImportError.

```
playwright>=1.40
mcp>=0.3
uvicorn>=0.20
```
