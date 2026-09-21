"""Data-driven tool registry + factory for the PagoMedios MCP server.

Supports the same modes as the factuplan registry plus no extras needed —
the fiscal tools live in tools/custom.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import server
from app import mcp


@dataclass(frozen=True)
class ToolSpec:
    name: str
    sig: str
    doc: str
    method: str
    path: str
    mode: str
    query: tuple[str, ...] = ()
    required: tuple[str, ...] = ()
    optional: tuple[str, ...] = ()


async def _dispatch(spec: ToolSpec, args: dict[str, Any]) -> str:
    path = spec.path.format(**args) if "{" in spec.path else spec.path
    params: dict[str, Any] | None = None
    body: dict[str, Any] | None = None

    if spec.mode == "params":
        params = {k: args[k] for k in spec.query} if spec.query else None
    elif spec.mode == "body":
        body = {k: args[k] for k in spec.required}
        body.update(server._drop_none({k: args[k] for k in spec.optional}))
    elif spec.mode == "body_literal":
        key = spec.required[0]
        body = {key: args[key]}
    else:
        raise ValueError(f"Unknown tool mode: {spec.mode!r}")

    kwargs: dict[str, Any] = {}
    if params is not None:
        kwargs["params"] = params
    if body is not None:
        kwargs["body"] = body
    result = await server._request(spec.method, path, **kwargs)
    return server._json(result)


_EXEC_GLOBALS = {"Any": Any}


def build_tool(spec: ToolSpec):
    src = (
        f"async def {spec.name}({spec.sig}) -> str:\n"
        f"    {spec.doc!r}\n"
        f"    return await __dispatch(__spec, locals())\n"
    )
    ns = dict(_EXEC_GLOBALS)
    ns["__dispatch"] = _dispatch
    ns["__spec"] = spec
    exec(compile(src, f"<tool:{spec.name}>", "exec"), ns)  # noqa: S102
    fn = ns[spec.name]
    fn.__doc__ = spec.doc
    fn.__module__ = "tools._registry"
    mcp.tool()(fn)
    return fn


def register_all(specs) -> dict[str, Any]:
    built: dict[str, Any] = {}
    for spec in specs:
        built[spec.name] = build_tool(spec)
    return built
