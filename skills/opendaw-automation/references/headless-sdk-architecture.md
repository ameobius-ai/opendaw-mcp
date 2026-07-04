# openDAW Headless SDK Implementation Strategy

Based on the architecture of `naomiaro/opendaw-test`, the `yjs-server` binary WebSocket protocol can be entirely bypassed for automation purposes by using the official headless SDK: `@opendaw/studio-sdk`.

## Core Concept
Instead of connecting to the external `yjs-server` via a websocket, the Agent runs the DAW engine in-memory using the SDK. Since openDAW heavily relies on `SharedArrayBuffer` and `AudioWorklets`, it must run in a browser environment with strict Cross-Origin Isolation headers.

## Implementation Steps
1. **Host:** Create a minimal HTML page that imports `@opendaw/studio-sdk` and initializes `Project.new()`.
2. **Serve:** Serve this page locally with the required COOP/COEP headers:
   ```http
   Cross-Origin-Opener-Policy: same-origin
   Cross-Origin-Embedder-Policy: require-corp
   ```
3. **Control:** Use Playwright or Puppeteer to open this page headlessly.
4. **RPC Bridge:** The FastMCP python server uses Playwright's `page.evaluate()` or CDP to execute JavaScript functions within the openDAW context (e.g., adding tracks, loading audio blobs).

## SDK Initialization Example
```javascript
import { Project, GlobalSampleLoaderManager } from "@opendaw/studio-core";

const audioContext = new AudioContext({ latencyHint: 0 });
const project = Project.new({
  audioContext,
  sampleManager: new GlobalSampleLoaderManager(...),
  // ... other dependencies
});
await project.engine.isReady();
```