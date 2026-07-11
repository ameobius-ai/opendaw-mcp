"""Pytest configuration: handle optional dependencies gracefully.

When playwright is not installed (e.g. collecting tests without a browser),
inject a mock module so `import server` and `from opendaw_mcp import ...`
succeed at collection time. Tests that actually need a live bridge should
use the `skipif(not playwright_available)` marker.
"""
import sys
from unittest.mock import MagicMock

playwright_available = True
try:
    import playwright  # noqa: F401
except ImportError:
    playwright_available = False

if not playwright_available:
    mock_pw = MagicMock()
    sys.modules["playwright"] = mock_pw
    sys.modules["playwright.async_api"] = mock_pw.async_api

# Mock scipy for collection if not installed
try:
    import scipy  # noqa: F401
except ImportError:
    if "scipy" not in sys.modules:
        sys.modules["scipy"] = MagicMock()
        sys.modules["scipy.signal"] = MagicMock()
        sys.modules["scipy.io"] = MagicMock()
        sys.modules["scipy.io.wavfile"] = MagicMock()

# Mock pyloudnorm for collection if not installed
try:
    import pyloudnorm  # noqa: F401
except ImportError:
    if "pyloudnorm" not in sys.modules:
        sys.modules["pyloudnorm"] = MagicMock()
