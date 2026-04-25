"""
Servidor MCP para PagoMedios V2 (Abitmedia) v2.0.0
=====================================================
Permite a un agente de IA gestionar pagos en línea, tokenización de tarjetas
y cobros recurrentes a través de la plataforma PagoMedios de Abitmedia.

URL base: https://api.abitmedia.cloud/pagomedios/v2
Auth: Bearer Token

MULTI-ACCOUNT SUPPORT (v2.0)
  Cada tool acepta `token` como parámetro explícito para soportar múltiples cuentas
  (personal, empresa, etc.) sin cambiar variables de entorno.

Módulos disponibles:
  · Solicitudes de pago  → envía link de cobro al cliente (email/SMS)
  · Links de pago        → genera URL reutilizable para compartir
  · Tarjetas (Cards)     → tokenización, cobro recurrente y eliminación
  · Reversos             → anula un cargo del mismo día
  · Configuraciones      → consulta ajustes del comercio

Fuente de verdad técnica: docs/openapi.yaml
"""

import os
import json
import logging
from typing import Any

from dotenv import load_dotenv
import httpx
from mcp.server.fastmcp import FastMCP

load_dotenv()


# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s", "level":"%(levelname)s", "name":"%(name)s", "message":"%(message)s"}',
)
logger = logging.getLogger("pagomedios-mcp")

PAGOMEDIOS_BASE_URL = os.environ.get(
    "PAGOMEDIOS_BASE_URL", "https://api.abitmedia.cloud/pagomedios/v2"
)

HTTP_TIMEOUT = float(os.environ.get("PAGOMEDIOS_HTTP_TIMEOUT", "30"))

mcp = FastMCP(
    "pagomedios",
    host="0.0.0.0",
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
        "IMPORTANT: "
        "  · Use a unique 'reference' per transaction to prevent duplicates. "
        "  · Reversals (reversar_cobro) are only available on the SAME DAY as the charge. "
        "  · Error 422 from cobrar_tarjeta: expired card, insufficient funds, or declined."
    ))

# ---------------------------------------------------------------------------
# Cliente HTTP reutilizable
# ---------------------------------------------------------------------------


def _resolve_token() -> str:
    """Return the PagoMedios Bearer token from environment."""
    resolved = os.environ.get("PAGOMEDIOS_BEARER_TOKEN", "")
    if not resolved:
        raise ValueError(
            "PAGOMEDIOS_BEARER_TOKEN env var is required. Configure it in your .env file."
        )
    return resolved


def _build_headers() -> dict[str, str]:
    """Build Authorization headers for a specific PagoMedios account."""
    return {
        "Authorization": f"Bearer {_resolve_token()}",
        "Content-Type": "application/json",
    }


async def _request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    body: dict[str, Any] | None = None) -> dict | list | str:
    """Execute an HTTP request against the PagoMedios API."""
    url = f"{PAGOMEDIOS_BASE_URL}{path}"
    if params:
        params = {k: v for k, v in params.items() if v is not None and v != ""}

    logger.info("%s %s", method.upper(), url)

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        resp = await client.request(
            method,
            url,
            headers=_build_headers(),
            params=params,
            json=body)
    logger.info("Respuesta HTTP %s", resp.status_code)

    if resp.status_code >= 400:
        return {
            "error": True,
            "status_code": resp.status_code,
            "detail": resp.text,
        }
    if not resp.text.strip():
        return {"ok": True, "status_code": resp.status_code}
    try:
        return resp.json()
    except Exception:
        return resp.text


# ═══════════════════════════════════════════════════════════════════════════
# SOLICITUDES DE PAGO  –  /payment-requests
# ═══════════════════════════════════════════════════════════════════════════


@mcp.tool()
async def listar_solicitudes_pago() -> str:
    """Retrieve the list of all payment requests created in PagoMedios.

    Use this tool to check the history of payment requests, their statuses,
    and amounts.

    REQUIRED PARAMETERS:

    RETURNS:
      List of payment request objects. Each item includes:
      id, amount, description, document, customer_name, customer_email, status.

    EXAMPLE CALL:
      listar_solicitudes_pago(token="eyJ...")
    """
    result = await _request("GET", "/payment-requests")
    return json.dumps(result, ensure_ascii=False, default=str)


@mcp.tool()
async def crear_solicitud_pago(    amount: float,
    description: str,
    document: str,
    customer_name: str,
    customer_email: str,
    tax: float = 0.0,
    reference: str | None = None,
    customer_phone: str | None = None) -> str:
    """⚠️ MUTATION — Create and send a payment request to a customer by email — POST /payment-requests.

    Use this tool to send a payment charge to a customer. They will receive an email
    with a button to complete the payment on the PagoMedios platform.
    Use crear_link_pago instead if you want a reusable link without sending an email.

    REQUIRED PARAMETERS:
      amount (float): Total amount to charge (tax inclusive). Example: 11.20
      description (str): Description of what is being charged. Example: "Monthly subscription"
      document (str): Customer cedula or RUC. Example: "0912345678"
      customer_name (str): Customer full name. Example: "Juan Pérez"
      customer_email (str): Customer email address where the request will be sent.
                            Example: "juan@example.com"

    OPTIONAL PARAMETERS:
      tax (float, default=0.0): VAT amount already included in 'amount'. Example: 1.50
      reference (str): Your internal system reference. Use a UUID to prevent duplicates
                       in case of retries. Example: "a1b2c3d4-..."
      customer_phone (str): Customer phone number for additional contact.

    RETURNS:
      {"id": str, "url": str, "status": str}

    EXAMPLE CALL:
      crear_solicitud_pago(
          token="eyJ...",
          amount=11.20, description="Invoice #001",
          document="0912345678", customer_name="Juan Pérez",
          customer_email="juan@example.com", tax=1.50
      )
    """
    body: dict[str, Any] = {
        "amount": amount,
        "description": description,
        "document": document,
        "customer_name": customer_name,
        "customer_email": customer_email,
        "tax": tax,
    }
    if reference is not None:
        body["reference"] = reference
    if customer_phone is not None:
        body["customer_phone"] = customer_phone

    result = await _request("POST", "/payment-requests", body=body)
    return json.dumps(result, ensure_ascii=False, default=str)


# ═══════════════════════════════════════════════════════════════════════════
# LINKS DE PAGO  –  /payment-links
# ═══════════════════════════════════════════════════════════════════════════


@mcp.tool()
async def listar_links_pago() -> str:
    """Retrieve the list of all payment links created in PagoMedios.

    Use this tool to check reusable payment links and their statuses.
    Payment links can be shared via WhatsApp, social media, or embedded in a website.

    REQUIRED PARAMETERS:

    RETURNS:
      List of payment link objects. Each item includes: id, amount, description, url, status.

    EXAMPLE CALL:
      listar_links_pago(token="eyJ...")
    """
    result = await _request("GET", "/payment-links")
    return json.dumps(result, ensure_ascii=False, default=str)


@mcp.tool()
async def crear_link_pago(    amount: float,
    description: str,
    reference: str | None = None,
    notify_url: str | None = None) -> str:
    """⚠️ MUTATION — Create a permanent, reusable payment link — POST /payment-links.

    Use this tool to generate a shareable payment URL. Unlike crear_solicitud_pago,
    this link can be shared multiple times (via WhatsApp, email, web button).

    REQUIRED PARAMETERS:
      amount (float): Fixed charge amount. Example: 25.00
      description (str): Description of the charge concept. Example: "Product catalog"

    OPTIONAL PARAMETERS:
      reference (str): Your internal reference for tracking. Example: "PLAN-BASIC"
      notify_url (str): Webhook URL that receives notification when someone pays
                        using this link.

    RETURNS:
      {"id": str, "url": str, "status": str}

    EXAMPLE CALL:
      crear_link_pago(token="eyJ...", amount=25.00, description="Product catalog")
    """
    body: dict[str, Any] = {
        "amount": amount,
        "description": description,
    }
    if reference is not None:
        body["reference"] = reference
    if notify_url is not None:
        body["notify_url"] = notify_url

    result = await _request("POST", "/payment-links", body=body)
    return json.dumps(result, ensure_ascii=False, default=str)


# ═══════════════════════════════════════════════════════════════════════════
# TARJETAS (TOKENIZACIÓN Y RECURRENCIA)  –  /cards
# ═══════════════════════════════════════════════════════════════════════════


@mcp.tool()
async def listar_tarjetas() -> str:
    """Retrieve all tokenized cards registered in the PagoMedios account.

    Use this tool to list saved card tokens before making a recurring charge.
    Tokens are required for cobrar_tarjeta.

    REQUIRED PARAMETERS:

    RETURNS:
      List of tokenized card objects. Each item includes:
      token, last4 digits, brand (VISA/MC), expiry, and holder_name.

    EXAMPLE CALL:
      listar_tarjetas(token="eyJ...")
    """
    result = await _request("GET", "/cards")
    return json.dumps(result, ensure_ascii=False, default=str)


@mcp.tool()
async def registrar_tarjeta(    card_number: str,
    exp_month: str,
    exp_year: str,
    cvv: str,
    holder_name: str) -> str:
    """⚠️ MUTATION — Register (tokenize) a credit or debit card for future charges — POST /cards/register.

    Use this tool to securely save a customer's card. The actual card number is NOT stored;
    a secure token is returned for future charges. This process is PCI DSS compliant.

    ⚠️ IMPORTANT: Card data is highly sensitive. Only use this in flows where the
    customer explicitly provides their card details to be saved for future use.

    REQUIRED PARAMETERS:
      card_number (str): 16-digit card number without spaces. Example: "4111111111111111"
      exp_month (str): Expiry month, 2 digits. Example: "07"
      exp_year (str): Expiry year, 4 digits. Example: "2027"
      cvv (str): Card security code. Example: "123"
      holder_name (str): Cardholder name exactly as printed on the card. Example: "JOHN DOE"

    RETURNS:
      {"token": str, "brand": str, "last4": str}  — use token in cobrar_tarjeta.

    EXAMPLE CALL:
      registrar_tarjeta(
          token="eyJ...", card_number="4111111111111111", exp_month="07",
          exp_year="2027", cvv="123", holder_name="JOHN DOE"
      )
    """
    body: dict[str, Any] = {
        "card_number": card_number,
        "exp_month": exp_month,
        "exp_year": exp_year,
        "cvv": cvv,
        "holder_name": holder_name,
    }
    result = await _request("POST", "/cards/register", body=body)
    return json.dumps(result, ensure_ascii=False, default=str)


@mcp.tool()
async def cobrar_tarjeta(    card_token: str,
    amount: float,
    description: str,
    tax: float = 0.0,
    reference: str | None = None) -> str:
    """⚠️ MUTATION — Charge a tokenized card directly — POST /cards/charge.

    Use this tool for recurring payments, subscriptions, or OneClick charges
    against a card that was previously saved with registrar_tarjeta.
    Save the returned transaction_id for potential reversals.

    REQUIRED PARAMETERS:
      card_token (str): Card token obtained from registrar_tarjeta or listar_tarjetas.
                        Example: "tok_abc123xyz"
      amount (float): Amount to charge (tax inclusive). Example: 29.99
      description (str): Charge description visible on the customer's bank statement.
                         Example: "Monthly Premium Plan"

    OPTIONAL PARAMETERS:
      tax (float, default=0.0): VAT amount already included in 'amount'. Example: 3.99
      reference (str): Unique internal ID. Use a UUID to prevent duplicate charges
                       on retry. Example: "SUB-2025-0042"

    RETURNS:
      {"transaction_id": str, "status": str, "authorization_code": str, "amount": float}

    COMMON ERRORS:
      422: Insufficient funds, expired card, or declined by the bank.

    EXAMPLE CALL:
      cobrar_tarjeta(token="eyJ...", card_token="tok_abc123xyz",
                     amount=29.99, description="Monthly Premium Plan", tax=3.99)
    """
    body: dict[str, Any] = {
        "token": card_token,
        "amount": amount,
        "description": description,
        "tax": tax,
    }
    if reference is not None:
        body["reference"] = reference

    result = await _request("POST", "/cards/charge", body=body)
    return json.dumps(result, ensure_ascii=False, default=str)


@mcp.tool()
async def eliminar_tarjeta(card_token: str) -> str:
    """⚠️ IRREVERSIBLE MUTATION — Delete a tokenized card from the PagoMedios vault — DELETE /cards/{token}.

    Use this tool when a customer asks to remove their saved card.
    Once deleted, the token cannot be used for future charges.

    REQUIRED PARAMETERS:
      card_token (str): Card token to delete (from registrar_tarjeta or listar_tarjetas).
                        Example: "tok_abc123xyz"

    RETURNS:
      {"ok": True, "status_code": int}  — confirmation of deletion.

    EXAMPLE CALL:
      eliminar_tarjeta(token="eyJ...", card_token="tok_abc123xyz")
    """
    result = await _request("DELETE", f"/cards/{card_token}")
    return json.dumps(result, ensure_ascii=False, default=str)


# ═══════════════════════════════════════════════════════════════════════════
# REVERSOS  –  /cards/reverse
# ═══════════════════════════════════════════════════════════════════════════


@mcp.tool()
async def reversar_cobro(    transaction_id: str,
    reason: str | None = None) -> str:
    """⚠️ MUTATION — Reverse (void) a card charge on the same day it was made — POST /cards/reverse.

    Use this tool to cancel a charge and return funds to the customer.
    REVERSALS ARE ONLY AVAILABLE ON THE SAME DAY as the original charge.
    For refunds on subsequent days, contact PagoMedios support directly.

    REQUIRED PARAMETERS:
      transaction_id (str): The transaction_id returned by cobrar_tarjeta.
                            Example: "TXN-2025-00123"

    OPTIONAL PARAMETERS:
      reason (str): Reason for the reversal (recommended for auditing).
                    Example: "Customer requested cancellation"

    RETURNS:
      {"ok": True/False, "status": str}  — reversal confirmation.

    EXAMPLE CALL:
      reversar_cobro(token="eyJ...", transaction_id="TXN-2025-00123",
                     reason="Customer cancellation")
    """
    body: dict[str, Any] = {"transaction_id": transaction_id}
    if reason is not None:
        body["reason"] = reason

    result = await _request("POST", "/cards/reverse", body=body)
    return json.dumps(result, ensure_ascii=False, default=str)


# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURACIONES  –  /settings
# ═══════════════════════════════════════════════════════════════════════════


@mcp.tool()
async def consultar_configuracion() -> str:
    """Retrieve the global commerce configuration from PagoMedios.

    Use this tool to check integration status, available payment methods,
    currency settings, and transaction limits before processing payments.

    REQUIRED PARAMETERS:

    RETURNS:
      {"company_name": str, "currency": str, "status": "active" | "inactive",
       "payment_methods": [...], "transaction_limits": {...}}

    EXAMPLE CALL:
      consultar_configuracion(token="eyJ...")
    """
    result = await _request("GET", "/settings")
    return json.dumps(result, ensure_ascii=False, default=str)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("MCP_PORT", 8000))
    transport_mode = os.getenv("MCP_TRANSPORT_MODE", "sse").lower()
    print(f"Starting PagoMedios MCP Server on http://0.0.0.0:{port}/mcp ({transport_mode})")
    if transport_mode == "sse":
        app = mcp.sse_app()
    elif transport_mode == "http_stream":
        app = mcp.streamable_http_app()
    else:
        raise ValueError(f"Unknown transport mode: {transport_mode}")
    uvicorn.run(app, host="0.0.0.0", port=port)
