#!/usr/bin/env python3
"""Minimal static file server with cross-origin isolation headers.

openDAW requires cross-origin isolation (SharedArrayBuffer / AudioWorklet),
so every response must carry COOP/COEP headers. Vite's dev server sets
these; this zero-dependency server does the same for a *pre-built* host
at a fraction of the RAM (~10 MB vs ~300-500 MB for Vite + Node).

Environment:
    OPENDAW_STATIC_DIR      Directory to serve (default: /opendaw/headless-daw/dist)
    OPENDAW_STATIC_HOST     Bind host (default: 0.0.0.0)
    OPENDAW_PORT            Bind port (default: 5174)
    OPENDAW_STATIC_VERBOSE  Set to 1 to enable request logging
"""

from __future__ import annotations

import http.server
import os

HOST = os.environ.get("OPENDAW_STATIC_HOST", "0.0.0.0")
PORT = int(os.environ.get("OPENDAW_PORT", "5174"))
DIRECTORY = os.environ.get("OPENDAW_STATIC_DIR", "/opendaw/headless-daw/dist")

_CACHEABLE = (".js", ".mjs", ".css", ".wasm", ".woff", ".woff2", ".png", ".svg")


class IsolatedHandler(http.server.SimpleHTTPRequestHandler):
    """Static handler that adds the headers openDAW needs to run."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        # Required for SharedArrayBuffer / AudioWorklet (crossOriginIsolated)
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
        self.send_header("Cross-Origin-Resource-Policy", "cross-origin")
        if self.path.endswith(_CACHEABLE):
            self.send_header("Cache-Control", "public, max-age=3600")
        super().end_headers()

    def log_message(self, format, *args):  # noqa: A002 - stdlib signature
        if os.environ.get("OPENDAW_STATIC_VERBOSE"):
            super().log_message(format, *args)


def main() -> None:
    server = http.server.ThreadingHTTPServer((HOST, PORT), IsolatedHandler)
    print(f"Serving {DIRECTORY} on http://{HOST}:{PORT} (COOP/COEP enabled)")
    server.serve_forever()


if __name__ == "__main__":
    main()
