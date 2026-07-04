#!/bin/bash
# Start Vite, generate Paulstretch preset, kill Vite — all in one process
set -e

VITE_DIR="/home/ameobius/projects/creative-studio/agent-daw/headless-daw"
MCP_DIR="/home/ameobius/projects/creative-studio/agent-daw/opendaw-mcp"

# Start Vite on 5174
cd "$VITE_DIR"
node node_modules/vite/bin/vite.js --port 5174 &
VITE_PID=$!
echo "Vite PID: $VITE_PID"

# Wait for Vite to be ready
for i in $(seq 1 15); do
  sleep 2
  CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5174/ 2>/dev/null || echo "000")
  echo "attempt $i: HTTP $CODE"
  if [ "$CODE" = "200" ]; then
    echo "Vite ready!"
    break
  fi
done

if [ "$CODE" != "200" ]; then
  echo "Vite failed to start, aborting"
  kill $VITE_PID 2>/dev/null
  exit 1
fi

# Run preset generation
cd "$MCP_DIR"
source venv/bin/activate
OPENDAW_URL=http://localhost:5174 python3 scripts/generate_presets.py 2>&1

# Kill Vite
kill $VITE_PID 2>/dev/null
echo "Done. Vite killed."
