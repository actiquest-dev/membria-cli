"""Entry point for MCP daemon subprocess."""

import logging
import sys
from pathlib import Path

from membria.mcp_daemon import MCPDaemonServer

# Setup logging
log_dir = Path.home() / ".membria" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_dir / "daemon.log"),
        logging.StreamHandler(sys.stderr),
    ],
)

logger = logging.getLogger(__name__)


def main():
    """Run the MCP daemon."""
    try:
        logger.info("Starting Membria MCP Daemon...")

        # Create and start real MCP daemon
        daemon = MCPDaemonServer()
        daemon.start()

    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Daemon error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("Daemon stopped")


if __name__ == "__main__":
    main()
