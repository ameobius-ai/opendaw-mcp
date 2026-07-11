import { defineConfig, type Plugin } from "vite"
import crossOriginIsolation from "vite-plugin-cross-origin-isolation"
import { existsSync, readFileSync, readdirSync, statSync } from "fs"
import { resolve, join, extname, sep } from "path"

const certKeyPath = "localhost-key.pem"
const certPath = "localhost.pem"
const hasLocalCerts = existsSync(certKeyPath) && existsSync(certPath)

// Serve WASM engine artifacts from @opendaw/studio-core-wasm/dist/wasm/ under /wasm-engine
const WASM_DIST = resolve(__dirname, "node_modules/@opendaw/studio-core-wasm/dist")
const WASM_SERVE_ROOT = resolve(WASM_DIST, "wasm")
const MIME: Record<string, string> = { ".wasm": "application/wasm", ".js": "text/javascript", ".map": "application/json" }

const wasmEngineAssets = (): Plugin => ({
  name: "wasm-engine-assets",
  apply: "serve",
  configureServer(server) {
    server.middlewares.use("/wasm-engine", (req, res, next) => {
      try {
        const rel = (req.url ?? "/").split("?")[0].replace(/^\/+/, "")
        const file = resolve(WASM_DIST, rel)
        if (!(file === WASM_SERVE_ROOT || file.startsWith(WASM_SERVE_ROOT + sep)) || !existsSync(file) || !statSync(file).isFile()) {
          return next()
        }
        res.setHeader("Content-Type", MIME[extname(file)] ?? "application/octet-stream")
        res.end(readFileSync(file))
      } catch (err) {
        console.error("[wasm-engine-assets] serve failed:", String(err))
        next()
      }
    })
  },
})

export default defineConfig({
  root: ".",
  build: { outDir: "dist" },
  server: {
    port: 5174,
    host: "0.0.0.0",
    ...(hasLocalCerts && {
      https: {
        key: readFileSync(certKeyPath),
        cert: readFileSync(certPath),
      },
    }),
    headers: {
      "Cross-Origin-Opener-Policy": "same-origin",
      "Cross-Origin-Embedder-Policy": "require-corp",
    },
  },
  plugins: [crossOriginIsolation(), wasmEngineAssets()],
  optimizeDeps: {
    exclude: [
      "@opendaw/studio-core",
      "@opendaw/studio-adapters",
      "@opendaw/studio-boxes",
      "@opendaw/lib-std",
      "@opendaw/lib-dsp",
      "@opendaw/lib-box",
      "@opendaw/lib-dom",
      "@opendaw/lib-runtime",
      "@opendaw/lib-midi",
      "@opendaw/lib-fusion",
      "@opendaw/studio-core-wasm",
    ],
  },
  worker: {
    format: "es",
  },
})
