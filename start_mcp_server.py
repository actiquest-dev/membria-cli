#!/usr/bin/env python
"""
Start Membria MCP Server for Claude Code integration.

Usage:
  python start_mcp_server.py

Or from Claude Code:
  Just add to Claude settings and it auto-starts
"""

import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """Start the MCP server."""
    try:
        from membria.mcp_server import start_mcp_server

        logger.info("Starting Membria MCP Server...")
        logger.info("Available tools:")
        logger.info("  • membria.capture_decision")
        logger.info("  • membria.record_outcome")
        logger.info("  • membria.get_calibration")
        logger.info("  • membria.get_decision_context")
        logger.info("  • membria.get_plan_context (PRE-PLAN)")
        logger.info("  • membria.validate_plan (MID-PLAN)")
        logger.info("  • membria.record_plan (POST-PLAN)")
        logger.info("")
        logger.info("Connected to Claude Code - ready for use")

        # Start server
        start_mcp_server()

    except KeyboardInterrupt:
        logger.info("MCP Server stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error starting MCP server: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
