# Agent-First Documentation: PagoMedios MCP Server

## 1. Contexto General
Servidor MCP para la plataforma PagoMedios (Abitmedia Cloud) — generación de
solicitudes de cobro, links de pago reutilizables, cobros con tarjeta
tokenizada y tracking.

## 2. Tecnologías Principales
- **FastMCP 3.3.1**.
- **httpx**: Cliente HTTP asíncrono.
- Header `Authorization: Bearer <PAGOMEDIOS_BEARER_TOKEN>`.

## 3. Reglas de Negocio
- **Montos en USD float**, pero el server los desglosa en `amount` (total con IVA) + `tax`.
  El motor fiscal `_calcular_amount_tax` es determinista: NO construirlo manualmente.
- **Reversos mismo día**: `reversar_cobro` solo aplica el mismo día calendario (zona horaria Ecuador UTC-5).
- Links de pago (`/payment-links`) son reutilizables; solicitudes (`/payment-requests`) son únicas.

## 4. Variables de Entorno
- `PAGOMEDIOS_BEARER_TOKEN`: Bearer token. **No es parámetro de tool**.
- `PAGOMEDIOS_BASE_URL`: URL base.
- `MCP_HOST`, `MCP_PORT` (default 8011), `MCP_TRANSPORT_MODE`.

## 5. Herramientas Principales (10 totales)
- `crear_solicitud_pago`: Envía una solicitud de pago por email.
- `crear_link_pago`: Genera link reusable.
- `cobrar_tarjeta`: Cobra una tarjeta tokenizada.
- `registrar_tarjeta`: Tokeniza una tarjeta.
- `eliminar_tarjeta`: Elimina token de tarjeta.
- `reversar_cobro`: Reversa un cobro (mismo día).
- `listar_solicitudes_pago`, `listar_links_pago`, `listar_tarjetas`, `consultar_configuracion`.

## 6. Consideraciones de Seguridad
- **Anti-SSRF en `notify_url`**: solo HTTPS, bloquea metadata IPs y rangos privados.
- **No loguear `PAGOMEDIOS_BEARER_TOKEN`** (filtrado automático).
- Reversos validan fecha: si la transacción no es del día actual (Ecuador), se rechaza.

## 7. Tests
- Pendiente: añadir cobertura mínima.
