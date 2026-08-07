"""
openDAW MCP Server — Modular Architecture
==========================================
Playwright bridge to a headless openDAW instance.
Every tool performs real operations via page.evaluate() into the V8 context
where the DAW project lives. No stubs, no placeholders.

Architecture:
  MCP Server (Python/FastMCP) → Playwright → headless Chromium → Vite :5174 → @opendaw/studio-sdk

Tools are organized in opendaw_mcp/tools/ modules and loaded lazily.
This file handles initialization, registration, and MCP server startup.
"""

import asyncio
import json
import logging
import math
import os
import atexit
import importlib

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

# Infrastructure imported from opendaw_mcp package
# All helpers re-exported for backward compatibility (tests, examples import from server)
from opendaw_mcp import (  # noqa: F401 — re-exported for backward compat
    HeadlessDawBridge,
    DAW_URL,
    TIDAL_RATE_MAP,
    DELAY_SYNC_MAP,
    WAVESHAPER_FUNCS,
    REVAMP_SECTIONS,
    _parse_wav,
    _compute_lufs,
    _ok,
    _err,
    _stable_seed,
    _wrap_eval,
    _unwrap_eval,
    _safe_filename,
    _safe_path,
    _clamp_script_param,
    _detect_bpm,
    _detect_key,
    _transcribe_drums,
    _transcribe_melody,
    _analyze_spectrum,
    _analyze_stereo,
    _analyze_dynamics,
    _resolve_audio_file,
    _load_wav_for_analysis,
    NOTE_TO_PITCH,
    CHORD_INTERVALS,
    SCALE_INTERVALS,
    GENRE_PRESETS,
    VALID_GENRES,
    parse_melody_pattern,
)

# Import tool modules
from opendaw_mcp.tools import (
    transport,
    tracks,
    instruments,
    effects,
    mixing,
    rendering,
    analysis,
    other,
)

# Setup logging
_LOG_FORMAT_JSON = os.environ.get("OPENDAW_MCP_LOG_JSON", "")
if _LOG_FORMAT_JSON:
    class _JsonFormatter(logging.Formatter):
        import json as _json
        def format(self, record):
            import json as _json, time as _time
            log = {
                "ts": _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime()),
                "level": record.levelname,
                "logger": record.name,
                "msg": record.getMessage(),
            }
            if hasattr(record, "tool"):
                log["tool"] = record.tool
            if hasattr(record, "duration_ms"):
                log["duration_ms"] = record.duration_ms
            if hasattr(record, "success"):
                log["success"] = record.success
            return _json.dumps(log)
    _handler = logging.StreamHandler()
    _handler.setFormatter(_JsonFormatter())
    logging.basicConfig(level=logging.INFO, handlers=[_handler])
else:
    logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _log_tool_call(tool_name: str):
    """Context manager/decorator for structured tool call logging."""
    import time as _time
    start = _time.perf_counter()
    def _finish(success: bool):
        elapsed_ms = round((_time.perf_counter() - start) * 1000, 1)
        extra = {"tool": tool_name, "duration_ms": elapsed_ms, "success": success}
        logger.info(f"tool_call: {tool_name}", extra=extra)
    return _finish


# Initialize MCP server
mcp = FastMCP("opendaw-mcp")
__version__ = "1.391.0"
DAW_HOST_DIR = os.environ.get("OPENDAW_HOST_DIR", os.path.join(os.path.dirname(__file__), "..", "headless-daw"))
EXPORT_DIR = os.environ.get("OPENDAW_EXPORT_DIR", os.path.join(os.path.dirname(__file__), "..", "exports"))
os.makedirs(EXPORT_DIR, exist_ok=True)

# Initialize bridge
bridge = HeadlessDawBridge()


def cleanup():
    try:
        asyncio.run(bridge.stop())
    except Exception:
        pass


atexit.register(cleanup)


# Initialize tool modules with shared dependencies
logger.info("Initializing tool modules...")
transport.init_transport_tools(bridge, _wrap_eval)
tracks.init_tracks_tools(bridge, _wrap_eval, _ok, _err)
instruments.init_instruments_tools(bridge, _wrap_eval, _ok, _err)
effects.init_effects_tools(bridge, _wrap_eval, _ok, _err)
mixing.init_mixing_tools(bridge, _wrap_eval, _ok, _err)
rendering.init_rendering_tools(bridge, _wrap_eval, _ok, _err)
analysis.init_analysis_tools(bridge, _wrap_eval, _ok, _err)
other.init_other_tools(bridge, _wrap_eval, _ok, _err)


# Register all tools with MCP
def register_tools():
    """Register all tools from modules with MCP server."""
    tool_modules = [
        ('transport', transport),
        ('tracks', tracks),
        ('instruments', instruments),
        ('effects', effects),
        ('mixing', mixing),
        ('rendering', rendering),
        ('analysis', analysis),
        ('other', other),
    ]
    
    total_registered = 0
    
    for module_name, module in tool_modules:
        for attr_name in dir(module):
            if attr_name.startswith('mcp_opendaw_'):
                func = getattr(module, attr_name)
                if callable(func):
                    # Determine if this should be read-only or destructive
                    annotations = ToolAnnotations()
                    
                    # Add appropriate annotations based on tool type
                    if 'get' in attr_name or 'list' in attr_name or 'analyze' in attr_name:
                        annotations.readOnlyHint = True
                    
                    # Register with MCP
                    # Note: We can't use @mcp.tool decorator here, so we use the registration API
                    mcp.tool()(func)
                    total_registered += 1
    
    logger.info(f"Registered {total_registered} tools with MCP server")
    return total_registered


# Register tools on startup
num_tools = register_tools()
logger.info(f"openDAW MCP Server v{__version__} ready with {num_tools} tools")


if __name__ == "__main__":
    import sys
    
    # Check for lite mode
    if os.environ.get("OPENDAW_MCP_MODE") == "lite":
        logger.info("Running in LITE mode (39 tools)")
        # In lite mode, we would only register a subset of tools
        # This is handled by the opendaw_mcp.lite_tools module
        from opendaw_mcp import lite_tools
        lite_tools.register_lite_tools(mcp, bridge)
    else:
        logger.info(f"Running in FULL mode ({num_tools} tools)")
    
    # Start server
    transport_mode = os.environ.get("MCP_TRANSPORT", "stdio")
    
    if transport_mode == "sse":
        import uvicorn
        host = os.environ.get("FASTMCP_HOST", "127.0.0.1")
        port = int(os.environ.get("FASTMCP_PORT", "8000"))
        logger.info(f"Starting SSE server on {host}:{port}")
        mcp.run(transport="sse")
    else:
        logger.info("Starting stdio server")
        mcp.run(transport="stdio")
