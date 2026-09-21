"""Spec table for data-driven PagoMedios tools (simple GET/DELETE tools).

Tools with fiscal pre-processing or complex logic live in tools/custom.py.
"""

from tools._registry import ToolSpec, register_all

SPECS = [
    ToolSpec(
        name="listar_solicitudes_pago",
        sig="",
        doc=(
            "Retrieve the list of all payment requests created in PagoMedios.\n\n"
            "    Use this tool to check the history of payment requests, their statuses,\n"
            "    and amounts.\n\n"
            "    RETURNS:\n"
            "      List of payment request objects. Each item includes:\n"
            "      id, amount, description, document, customer_name, customer_email, status.\n"
            "    "
        ),
        method="GET",
        path="/payment-requests",
        mode="params",
    ),
    ToolSpec(
        name="listar_links_pago",
        sig="",
        doc=(
            "Retrieve the list of all payment links created in PagoMedios.\n\n"
            "    Use this tool to check reusable payment links and their statuses.\n"
            "    Payment links can be shared via WhatsApp, social media, or embedded in a website.\n\n"
            "    RETURNS:\n"
            "      List of payment link objects. Each item includes: id, amount, description, url, status.\n"
            "    "
        ),
        method="GET",
        path="/payment-links",
        mode="params",
    ),
    ToolSpec(
        name="listar_tarjetas",
        sig="",
        doc=(
            "Retrieve all tokenized cards registered in the PagoMedios account.\n\n"
            "    Use this tool to list saved card tokens before making a recurring charge.\n"
            "    Tokens are required for cobrar_tarjeta.\n\n"
            "    RETURNS:\n"
            "      List of tokenized card objects. Each item includes:\n"
            "      token, last4 digits, brand (VISA/MC), expiry, and holder_name.\n"
            "    "
        ),
        method="GET",
        path="/cards",
        mode="params",
    ),
    ToolSpec(
        name="registrar_tarjeta",
        sig=(
            "card_number: str, "
            "exp_month: str, "
            "exp_year: str, "
            "cvv: str, "
            "holder_name: str"
        ),
        doc=(
            "⚠️ MUTATION — Register (tokenize) a credit or debit card for future charges — POST /cards/register.\n\n"
            "    REQUIRED PARAMETERS:\n"
            "      card_number (str): 16-digit card number without spaces. Example: \"4111111111111111\"\n"
            "      exp_month (str): Expiry month, 2 digits. Example: \"07\"\n"
            "      exp_year (str): Expiry year, 4 digits. Example: \"2027\"\n"
            "      cvv (str): Card security code. Example: \"123\"\n"
            "      holder_name (str): Cardholder name exactly as printed on the card. Example: \"JOHN DOE\"\n\n"
            "    RETURNS:\n"
            "      {\"token\": str, \"brand\": str, \"last4\": str}  — use token in cobrar_tarjeta.\n"
            "    "
        ),
        method="POST",
        path="/cards/register",
        mode="body",
        required=("card_number", "exp_month", "exp_year", "cvv", "holder_name"),
    ),
    ToolSpec(
        name="eliminar_tarjeta",
        sig="card_token: str",
        doc=(
            "⚠️ IRREVERSIBLE MUTATION — Delete a tokenized card from the PagoMedios vault — DELETE /cards/{card_token}.\n\n"
            "    REQUIRED PARAMETERS:\n"
            "      card_token (str): Card token to delete. Example: \"tok_abc123xyz\"\n\n"
            "    RETURNS:\n"
            "      {\"ok\": True, \"status_code\": int}  — confirmation of deletion.\n"
            "    "
        ),
        method="DELETE",
        path="/cards/{card_token}",
        mode="params",
    ),
    ToolSpec(
        name="consultar_configuracion",
        sig="",
        doc=(
            "Retrieve the global commerce configuration from PagoMedios.\n\n"
            "    Use this tool to check integration status, available payment methods,\n"
            "    currency settings, and transaction limits before processing payments.\n\n"
            "    RETURNS:\n"
            "      {\"company_name\": str, \"currency\": str, \"status\": \"active\" | \"inactive\",\n"
            "       \"payment_methods\": [...], \"transaction_limits\": {...}}\n"
            "    "
        ),
        method="GET",
        path="/settings",
        mode="params",
    ),
]

TOOLS = register_all(SPECS)
