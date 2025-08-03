#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Startup script for RPA Balance Loader API
This script starts the FastAPI server that provides HTTP API access to the browser automation functionality.
"""

import os
import sys
import logging
import uvicorn
from pathlib import Path

# Add bot directory to Python path
bot_dir = Path(__file__).parent / "bot"
sys.path.insert(0, str(bot_dir))

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def main():
    """Start the RPA API server"""
    try:
        # Get configuration from environment
        host = os.getenv("RPA_API_HOST", "0.0.0.0")  # Listen on all interfaces for external access
        port = int(os.getenv("RPA_API_PORT", 8001))
        
        logger.info("=" * 50)
        logger.info("RPA Balance Loader API Server")
        logger.info("=" * 50)
        logger.info(f"Starting API server on {host}:{port}")
        logger.info("This server provides HTTP API access to browser automation")
        logger.info("API Endpoints:")
        logger.info(f"  - POST http://{host}:{port}/api/create-user")
        logger.info(f"  - GET  http://{host}:{port}/health")
        logger.info(f"  - GET  http://{host}:{port}/")
        logger.info("=" * 50)
        
        # Start the FastAPI server
        uvicorn.run(
            "bot.api_server:app",
            host=host,
            port=port,
            log_level="info",
            reload=False,
            access_log=True
        )
        
    except KeyboardInterrupt:
        logger.info("API server stopped by user")
    except Exception as e:
        logger.error(f"Failed to start API server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()