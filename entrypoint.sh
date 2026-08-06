#!/bin/bash
set -e

# Serve the openDAW headless host on :5174.
# OPENDAW_SERVE_MODE=static uses the zero-dependency Python static server
# (requires a pre-built host in OPENDAW_STATIC_DIR). Default: Vite dev server.
if [ "${OPENDAW_SERVE_MODE:-vite}" = "static" ]; then
    echo "Static mode: serving ${OPENDAW_STATIC_DIR:-/opendaw/headless-daw/dist}"
    python3 /app/opendaw-mcp/scripts/serve_static.py &
else
    cd /opendaw/headless-daw
    node node_modules/vite/bin/vite.js --port 5174 --host 0.0.0.0 &
fi

# Wait for the host server to be ready
echo "Waiting for the host server..."
for i in $(seq 1 30); do
    if curl -s http://localhost:5174 > /dev/null 2>&1; then
        echo "Host server is ready"
        break
    fi
    sleep 1
done

# Start the MCP server in SSE mode (Glama introspection-ready)
cd /app/opendaw-mcp
export MCP_TRANSPORT=sse
export FASTMCP_HOST=0.0.0.0
export FASTMCP_PORT=8080
exec venv/bin/python server.py
