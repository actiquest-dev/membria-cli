"""Entry point for daemon subprocess."""

import logging
import sys
from pathlib import Path

from membria.daemon import MembriaDaemon
from membria.config import ConfigManager
from membria.mcp_server import MembriaMCPServer

# Setup logging
log_dir = Path.home() / ".membria" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_dir / "daemon.log"),
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)


def main():
    """Run the daemon."""
    try:
        logger.info("Starting Membria daemon...")

        # Initialize config
        config = ConfigManager()
        daemon_config = config.get()

        # Create and start daemon
        daemon = MembriaDaemon()
        if not daemon.initialize():
            logger.error("Failed to initialize daemon")
            sys.exit(1)

        logger.info("Daemon initialized successfully")

        # Create MCP server
        mcp_server = MembriaMCPServer()
        if not mcp_server.start():
            logger.error("Failed to start MCP server")
            sys.exit(1)

        logger.info(f"MCP server running on port {daemon_config.get('daemon', {}).get('port', 3117)}")

        # Keep daemon running
        import time
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")

    except Exception as e:
        logger.error(f"Daemon error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("Daemon stopped")


if __name__ == "__main__":
    main()
