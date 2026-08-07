#!/bin/bash
set -e

# Serve openDAW headless host on :5174
# OPENDAW_SERVE_MODE=static: Python static server (default, ~10MB RAM)
# OPENDAW_SERVE_MODE=vite: Vite dev server (~300-500MB RAM)

SERVE_MODE="${OPENDAW_SERVE_MODE:-static}"

if [ "$SERVE_MODE" = "static" ]; then
    STATIC_DIR="${OPENDAW_STATIC_DIR:-/opendaw/headless-daw/dist}"

    if [ ! -d "$STATIC_DIR" ]; then
        echo "ERROR: Static directory not found: $STATIC_DIR"
        exit 1
    fi

    echo "Static mode: serving $STATIC_DIR (~10 MB RAM)"
    python3 /app/opendaw-mcp/scripts/serve_static.py &
    STATIC_PID=$!

else
    echo "Vite mode: starting dev server (~300-500 MB RAM)"

    if ! command -v node &> /dev/null; then
        echo "ERROR: Node.js not found"
        exit 1
    fi

    cd /opendaw/headless-daw
    node node_modules/vite/bin/vite.js --port 5174 --host 0.0.0.0 &
    VITE_PID=$!
fi

# Wait for host server
echo "Waiting for host server..."
for i in $(seq 1 30); do
    if curl -s http://localhost:5174 > /dev/null 2>&1; then
        echo "Host server ready"
        break
    fi
    sleep 1
done

# Start MCP server
cd /app/opendaw-mcp
export MCP_TRANSPORT=sse
export FASTMCP_HOST=0.0.0.0
export FASTMCP_PORT=8080

echo "Starting MCP server on port 8080"
exec python3 server.py
