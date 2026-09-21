"""
PagoMedios — custom tools with fiscal pre-processing or complex logic.

Tools that call _calcular_amount_tax before building the request body, or
that have multi-step logic (reversar_cobro with Ecuador timezone check),
are implemented here as explicit @mcp.tool() functions.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

from mcp_common.security import validate_safe_url, validate_amount

import server
from _fiscal import TipoMonto, calcular_amount_tax
from app import mcp


@mcp.tool()
async def crear_solicitud_pago(
    monto: float,
    description: str,
    document: str,
    customer_name: str,
    customer_email: str,
    tipo_monto: TipoMonto = TipoMonto.SUBTOTAL,
    reference: str | None = None,
    customer_phone: str | None = None,
) -> str:
    """⚠️ MUTATION — Create and send a payment request to a customer by email — POST /payment-requests.

    MONETARY INPUT (agent MUST follow this contract):
      monto (float): The EXACT amount the user stated — pass it verbatim, no rounding.
      tipo_monto (enum):
        · "subtotal"      → monto is the taxable base WITHOUT IVA (default).
        · "total_con_iva" → monto is the final price ALREADY INCLUDING IVA.

    REQUIRED PARAMETERS:
      monto (float): Amount exactly as stated by the user. Example: 30.0
      description (str): Description of what is being charged.
      document (str): Customer cedula or RUC. Example: "0912345678"
      customer_name (str): Customer full name.
      customer_email (str): Customer email address where the request will be sent.

    OPTIONAL PARAMETERS:
      tipo_monto (str, default="subtotal"): "subtotal" | "total_con_iva".
      reference (str): Your internal system reference. Use a UUID to prevent duplicates.
      customer_phone (str): Customer phone number.

    RETURNS:
      {"id": str, "url": str, "status": str}
    """
    validate_amount(monto, "monto")
    amount_total, tax_iva = calcular_amount_tax(monto, tipo_monto)

    server.logger.info(
        "[crear_solicitud_pago] monto=%.2f tipo=%s → amount=%.2f tax=%.2f",
        monto, tipo_monto.value, amount_total, tax_iva,
    )

    body: dict[str, Any] = {
        "amount": amount_total,
        "description": description,
        "document": document,
        "customer_name": customer_name,
        "customer_email": customer_email,
        "tax": tax_iva,
    }
    if reference is not None:
        body["reference"] = reference
    if customer_phone is not None:
        body["customer_phone"] = customer_phone

    result = await server._request("POST", "/payment-requests", body=body)
    return server._json(result)


@mcp.tool()
async def crear_link_pago(
    monto: float,
    description: str,
    tipo_monto: TipoMonto = TipoMonto.SUBTOTAL,
    reference: str | None = None,
    notify_url: str | None = None,
) -> str:
    """⚠️ MUTATION — Create a permanent, reusable payment link — POST /payment-links.

    MONETARY INPUT (agent MUST follow this contract):
      monto (float): The EXACT amount the user stated — pass it verbatim, no rounding.
      tipo_monto (enum):
        · "subtotal"      → monto is the taxable base WITHOUT IVA (default).
        · "total_con_iva" → monto is the final price ALREADY INCLUDING IVA.

    REQUIRED PARAMETERS:
      monto (float): Amount exactly as stated by the user. Example: 25.0
      description (str): Description of the charge concept.

    OPTIONAL PARAMETERS:
      tipo_monto (str, default="subtotal"): "subtotal" | "total_con_iva".
      reference (str): Your internal reference for tracking.
      notify_url (str): Webhook URL that receives notification when someone pays.

    RETURNS:
      {"id": str, "url": str, "status": str}
    """
    amount_total, _ = calcular_amount_tax(monto, tipo_monto)

    server.logger.info(
        "[crear_link_pago] monto=%.2f tipo=%s → amount=%.2f",
        monto, tipo_monto.value, amount_total,
    )

    body: dict[str, Any] = {
        "amount": amount_total,
        "description": description,
    }
    if reference is not None:
        body["reference"] = reference
    if notify_url is not None:
        body["notify_url"] = validate_safe_url(notify_url, "notify_url")

    result = await server._request("POST", "/payment-links", body=body)
    return server._json(result)


@mcp.tool()
async def cobrar_tarjeta(
    card_token: str,
    monto: float,
    description: str,
    tipo_monto: TipoMonto = TipoMonto.SUBTOTAL,
    reference: str | None = None,
) -> str:
    """⚠️ MUTATION — Charge a tokenized card directly — POST /cards/charge.

    MONETARY INPUT (agent MUST follow this contract):
      monto (float): The EXACT amount the user stated — pass it verbatim, no rounding.
      tipo_monto (enum):
        · "subtotal"      → monto is the taxable base WITHOUT IVA (default).
        · "total_con_iva" → monto is the final price ALREADY INCLUDING IVA.

    REQUIRED PARAMETERS:
      card_token (str): Card token obtained from registrar_tarjeta or listar_tarjetas.
      monto (float): Amount exactly as stated by the user. Example: 29.99
      description (str): Charge description visible on the customer's bank statement.

    OPTIONAL PARAMETERS:
      tipo_monto (str, default="subtotal"): "subtotal" | "total_con_iva".
      reference (str): Unique internal ID. Use a UUID to prevent duplicate charges on retry.

    RETURNS:
      {"transaction_id": str, "status": str, "authorization_code": str, "amount": float}
    """
    validate_amount(monto, "monto")
    amount_total, tax_iva = calcular_amount_tax(monto, tipo_monto)

    server.logger.info(
        "[cobrar_tarjeta] monto=%.2f tipo=%s → amount=%.2f tax=%.2f",
        monto, tipo_monto.value, amount_total, tax_iva,
    )

    body: dict[str, Any] = {
        "token": card_token,
        "amount": amount_total,
        "description": description,
        "tax": tax_iva,
    }
    if reference is not None:
        body["reference"] = reference

    result = await server._request("POST", "/cards/charge", body=body)
    return server._json(result)


@mcp.tool()
async def reversar_cobro(
    transaction_id: str,
    reason: str | None = None,
    verify_status: bool = True,
) -> str:
    """⚠️ MUTATION — Reverse (void) a card charge on the same day it was made — POST /cards/reverse.

    REVERSALS ARE ONLY AVAILABLE ON THE SAME DAY as the original charge.

    REQUIRED PARAMETERS:
      transaction_id (str): The transaction_id returned by cobrar_tarjeta.

    OPTIONAL PARAMETERS:
      reason (str): Reason for the reversal (recommended for auditing).
      verify_status (bool, default=True): Validate the same-day reversal window.

    RETURNS:
      {"ok": True/False, "status": str, "pre_check": dict | None}
    """
    pre_check: dict | None = None
    if verify_status:
        ecuador_offset = timedelta(hours=-5)
        ecuador_now = datetime.now(timezone.utc).astimezone(timezone(ecuador_offset))
        ecuador_today = ecuador_now.date()
        pre_check = {
            "ecuador_date": ecuador_today.isoformat(),
            "ecuador_time": ecuador_now.isoformat(),
            "same_day_window": True,
        }
        m = re.search(r"TXN-\d{4}-(\d{2})(\d{2})", transaction_id)
        if m:
            try:
                txn_date = datetime(
                    int(re.search(r"TXN-(\d{4})", transaction_id).group(1)),
                    int(m.group(1)),
                    int(m.group(2)),
                    tzinfo=timezone(ecuador_offset),
                ).date()
                if txn_date != ecuador_today:
                    raise ValueError(
                        f"La transacción {transaction_id} es de {txn_date.isoformat()}, "
                        f"pero los reversos PagoMedios solo aplican el mismo día ({ecuador_today.isoformat()}). "
                        "Para devoluciones de días posteriores contacta a soporte de PagoMedios. "
                        "Si aún necesitas intentar, pasa verify_status=False."
                    )
                pre_check["transaction_date"] = txn_date.isoformat()
            except (ValueError, AttributeError) as exc:
                if "no aplican" in str(exc):
                    raise

    body: dict[str, Any] = {"transaction_id": transaction_id}
    if reason is not None:
        body["reason"] = reason

    result = await server._request("POST", "/cards/reverse", body=body)
    if pre_check is not None and isinstance(result, dict):
        result["pre_check"] = pre_check
    return server._json(result)
