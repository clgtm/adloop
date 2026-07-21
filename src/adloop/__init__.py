"""AdLoop — MCP server connecting Google Ads + GA4 + codebase."""

import os
import sys
from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("adloop")
except PackageNotFoundError:  # running from a source tree without install
    __version__ = "0.0.0.dev0"


def _mcp_run_options() -> dict[str, str | int]:
    """Build FastMCP launch options for the explicitly configured hosted transport.

    Args:
        None.

    Returns:
        Empty options for local stdio, or HTTP transport options bound to the Cloud Run port.

    Raises:
        ValueError: If ``PORT`` is set to a non-integer value for an HTTP deployment.
    """
    if os.environ.get("ADLOOP_TRANSPORT", "").strip().lower() != "http":
        return {}

    return {
        "transport": "http",
        "host": os.environ.get("ADLOOP_HOST", "0.0.0.0"),
        "port": int(os.environ.get("PORT", "8080")),
    }


def main() -> None:
    """Start the CLI or MCP server while retaining stdio as the local default.

    Args:
        None. Command behavior is selected from process arguments and deployment environment variables.

    Returns:
        None. The selected CLI action completes or the MCP server runs until it is stopped.
    """
    args = sys.argv[1:]

    if args and args[0] in ("--version", "-V"):
        print(f"adloop {__version__}")
        return

    if args and args[0] == "init":
        from adloop.cli import run_init_wizard

        try:
            run_init_wizard()
        except KeyboardInterrupt:
            print("\n\n  Setup cancelled.\n")
            sys.exit(130)
        return

    if args and args[0] in ("install-rules", "update-rules", "uninstall-rules"):
        from adloop.cli import run_rules_command

        try:
            sys.exit(run_rules_command(args[0], args[1:]))
        except KeyboardInterrupt:
            print("\n\n  Cancelled.\n")
            sys.exit(130)
        return

    # Process-global side effects (signal handlers, heartbeat thread, and
    # the stdio cancellation-race monkeypatch) are deliberately installed
    # here — in the stdio entry point — rather than at adloop.server import
    # time, so embedding the server in an ASGI app stays side-effect-free.
    from adloop import _mcp_patches, diagnostics

    diagnostics.install()
    _mcp_patches.install()

    from adloop.server import mcp

    mcp.run(**_mcp_run_options())
