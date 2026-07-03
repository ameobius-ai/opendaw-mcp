#!/bin/bash
set -e

# Start Vite dev server for openDAW headless-daw
cd /opendaw/headless-daw
node node_modules/vite/bin/vite.js --port 5174 --host 0.0.0.0 &
VITE_PID=$!

# Wait for Vite to be ready
echo "Waiting for Vite dev server..."
for i in $(seq 1 30); do
    if curl -s http://localhost:5174 > /dev/null 2>&1; then
        echo "Vite is ready"
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
