"""
PagoMedios MCP Server
=====================
MCP server for PagoMedios V2 (Abitmedia) — online payments platform for Ecuador.

Technical reference: docs/openapi.yaml

This module is the canonical runtime namespace. It re-exports config, HTTP
helpers, and the logger, then imports tools.specs and tools.custom so every
@mcp.tool() decorator registers on the shared `mcp` instance.
"""

from config import (  # noqa: F401
    PAGOMEDIOS_BASE_URL,
    HTTP_TIMEOUT,
    logger,
)
from app import mcp  # noqa: F401
from _http import (  # noqa: F401
    _build_headers,
    _request,
    _json,
    _drop_none,
)

# Data-driven tools (simple GET/POST without fiscal pre-processing)
import tools.specs  # noqa: F401, E402

# Custom tools (fiscal pre-processing: crear_solicitud_pago, crear_link_pago,
# cobrar_tarjeta, reversar_cobro)
import tools.custom  # noqa: F401, E402

__all__ = ["mcp", "_request", "_json", "_drop_none", "logger"]
