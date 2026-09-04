"""MCP bridge package: workbench tools for dsh's MCP client.

Kept import-free on purpose: the server entry point runs as
``python -m dsh_bridge.mcp_server``, and importing the server module from
this ``__init__`` first triggers a RuntimeWarning about the double import
(plus wasted tesseract-less import cost in every interpreter).
"""

__all__: list[str] = []
