"""
PagoMedios MCP Server — configuration module.
"""

import logging
import os

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s", "level":"%(levelname)s", "name":"%(name)s", "message":"%(message)s"}',
)
logger = logging.getLogger("pagomedios-mcp")

# ---------------------------------------------------------------------------
# Runtime flags
# ---------------------------------------------------------------------------

PAGOMEDIOS_BASE_URL: str = os.environ.get(
    "PAGOMEDIOS_BASE_URL", "https://api.abitmedia.cloud/pagomedios/v2"
)

HTTP_TIMEOUT: float = float(os.environ.get("PAGOMEDIOS_HTTP_TIMEOUT", "30"))
