"""
Health Check Endpoints for openDAW MCP
=======================================

Provides HTTP endpoints for monitoring and orchestration:
- /health - Liveness probe
- /ready - Readiness probe
- /metrics - Prometheus metrics (future)
"""

import asyncio
import json
import logging
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from typing import Dict, Any
import os

logger = logging.getLogger(__name__)


class HealthCheckHandler(BaseHTTPRequestHandler):
    """HTTP request handler for health check endpoints."""
    
    bridge = None
    
    def log_message(self, format, *args):
        logger.debug(format % args)
    
    def _send_json_response(self, status_code: int, data: Dict[str, Any]):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode('utf-8'))
    
    def do_GET(self):
        if self.path == '/health':
            self._handle_health()
        elif self.path == '/ready':
            self._handle_ready()
        elif self.path == '/metrics':
            self._handle_metrics()
        else:
            self._send_json_response(404, {"error": "Not found"})
    
    def _handle_health(self):
        response = {
            "status": "healthy",
            "timestamp": time.time(),
            "version": "1.0.0"
        }
        self._send_json_response(200, response)
    
    def _handle_ready(self):
        checks = {
            "bridge": self._check_bridge(),
            "browser": self._check_browser(),
            "daw_host": self._check_daw_host()
        }
        
        all_ready = all(check["status"] == "ok" for check in checks.values())
        
        response = {
            "status": "ready" if all_ready else "not_ready",
            "timestamp": time.time(),
            "checks": checks
        }
        
        status_code = 200 if all_ready else 503
        self._send_json_response(status_code, response)
    
    def _handle_metrics(self):
        response = {
            "status": "ok",
            "timestamp": time.time(),
            "metrics": {
                "note": "Prometheus metrics integration coming soon"
            }
        }
        self._send_json_response(200, response)
    
    def _check_bridge(self) -> Dict[str, Any]:
        if self.bridge is None:
            return {"status": "error", "message": "Bridge not initialized"}
        
        try:
            if hasattr(self.bridge, 'is_connected'):
                if self.bridge.is_connected():
                    return {"status": "ok", "message": "Bridge connected"}
                else:
                    return {"status": "error", "message": "Bridge not connected"}
            else:
                return {"status": "ok", "message": "Bridge initialized"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def _check_browser(self) -> Dict[str, Any]:
        if self.bridge is None:
            return {"status": "error", "message": "Bridge not initialized"}
        
        try:
            if hasattr(self.bridge, 'page'):
                if self.bridge.page is not None:
                    return {"status": "ok", "message": "Browser running"}
                else:
                    return {"status": "error", "message": "Browser not running"}
            else:
                return {"status": "unknown", "message": "Cannot check browser status"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def _check_daw_host(self) -> Dict[str, Any]:
        try:
            import urllib.request
            daw_url = os.environ.get("OPENDAW_URL", "http://localhost:5174")
            
            req = urllib.request.Request(daw_url, method='HEAD')
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    return {"status": "ok", "message": f"DAW host accessible at {daw_url}"}
                else:
                    return {"status": "error", "message": f"DAW host returned status {response.status}"}
        except Exception as e:
            return {"status": "error", "message": f"Cannot reach DAW host: {str(e)}"}


class HealthCheckServer:
    """HTTP server for health check endpoints."""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8081, bridge=None):
        self.host = host
        self.port = port
        self.bridge = bridge
        self.server = None
        self.thread = None
    
    def start(self):
        HealthCheckHandler.bridge = self.bridge
        
        self.server = HTTPServer((self.host, self.port), HealthCheckHandler)
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        
        logger.info(f"Health check server started on http://{self.host}:{self.port}")
        logger.info(f"  - GET /health  (liveness probe)")
        logger.info(f"  - GET /ready   (readiness probe)")
        logger.info(f"  - GET /metrics (metrics endpoint)")
    
    def stop(self):
        if self.server:
            self.server.shutdown()
            logger.info("Health check server stopped")
