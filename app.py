"""PagoMedios FastMCP application instance."""

import os

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "pagomedios",
    host=os.getenv("MCP_HOST", "0.0.0.0"),  # nosec B104
    instructions=(
        "MCP server for PagoMedios V2 (Abitmedia), an online payments platform for Ecuador. "
        "Supports payment requests (sent by email to the customer), reusable payment links, "
        "card tokenization for recurring charges, direct card charges, reversals, and "
        "commerce configuration queries. "
        "Credentials are loaded from PAGOMEDIOS_BEARER_TOKEN env var. "
        "MAIN FLOWS: "
        "  · One-time charge: crear_solicitud_pago → customer receives email with a pay button. "
        "  · Recurring charge: registrar_tarjeta → cobrar_tarjeta. "
        "  · Shareable link: crear_link_pago → share URL via WhatsApp or web. "
        "MONETARY INPUT RULES (agent must follow strictly): "
        "  · Pass `monto` (float) with the EXACT number the user stated. "
        "  · Pass `tipo_monto`='subtotal' if the amount is WITHOUT IVA (default). "
        "  · Pass `tipo_monto`='total_con_iva' if the amount ALREADY INCLUDES IVA. "
        "  · NEVER compute tax or totals yourself. The server does it deterministically. "
        "IMPORTANT: "
        "  · Use a unique 'reference' per transaction to prevent duplicates. "
        "  · Reversals (reversar_cobro) are only available on the SAME DAY as the charge. "
        "  · Error 422 from cobrar_tarjeta: expired card, insufficient funds, or declined. "
        "The IVA rate is read from IVA_EC_PERCENTAGE env var (default 15%)."
    ),
)
