"""
PagoMedios — deterministic fiscal engine.

The LLM NEVER calculates taxes. It passes `monto` + `tipo_monto` and this
module produces the correct `amount` (total with IVA) and `tax` (IVA amount)
as floats, as expected by the PagoMedios API.
"""

from __future__ import annotations

import os
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum

_TWO = Decimal("0.01")


class TipoMonto(str, Enum):
    """Whether the user-supplied amount includes IVA or is the taxable base."""

    SUBTOTAL = "subtotal"        # base WITHOUT IVA (default)
    TOTAL_CON_IVA = "total_con_iva"  # total WITH IVA already included


def _iva_rate() -> Decimal:
    """Read IVA_EC_PERCENTAGE from environment. Fallback: 0.15 (15%)."""
    raw = os.environ.get("IVA_EC_PERCENTAGE", "0.15")
    try:
        rate = Decimal(raw)
        if not (Decimal(0) < rate <= Decimal(1)):
            raise ValueError()
        return rate
    except Exception:
        raise ValueError(
            f"IVA_EC_PERCENTAGE inválido: {raw!r}. "
            "Debe ser un decimal entre 0 y 1, ej. '0.15' para 15%."
        )


def _r2(v: Decimal) -> Decimal:
    return v.quantize(_TWO, rounding=ROUND_HALF_UP)


def calcular_amount_tax(monto: float, tipo: TipoMonto) -> tuple[float, float]:
    """Return (amount_total, tax_iva) as floats for the PagoMedios API.

    PagoMedios expects:
        amount → total to charge (subtotal + IVA)
        tax    → IVA amount included in `amount`

    Examples:
        calcular_amount_tax(30.0, SUBTOTAL)      → (34.50, 4.50)
        calcular_amount_tax(30.0, TOTAL_CON_IVA) → (30.00, 3.91)
    """
    if monto <= 0:
        raise ValueError(f"monto debe ser > 0. Recibido: {monto}")
    rate = _iva_rate()
    d = Decimal(str(monto))

    if tipo == TipoMonto.TOTAL_CON_IVA:
        total = _r2(d)
        subtotal = _r2(d / (1 + rate))
        iva = _r2(total - subtotal)
    else:
        subtotal = _r2(d)
        iva = _r2(d * rate)
        total = _r2(subtotal + iva)

    return float(total), float(iva)
