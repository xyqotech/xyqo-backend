#!/usr/bin/env python3
"""
XYQO Contract Reader - Render Entry Point
Optimized entry point for Render deployment with persistent workers
"""

import os
import sys
import logging

# Configure logging early
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Main entry point with error handling"""
    try:
        logger.info("=== XYQO Backend Starting ===")
        
        # Render configuration
        port = int(os.environ.get("PORT", 8000))
        host = "0.0.0.0"
        
        logger.info(f"Port: {port}, Host: {host}")
        
        try:
            # Environment validation
            openai_key = os.getenv("OPENAI_API_KEY")
            if not openai_key:
                logger.error("CRITICAL: OPENAI_API_KEY not set")
                # Allow startup without OpenAI key for health checks
                logger.warning("Starting without OpenAI API key - only health endpoint will work")
            
            # Import FastAPI app after environment validation
            from app.main import app
            
            # Server configuration - Render provides PORT dynamically
            port = int(os.environ.get("PORT", 8000))
            host = "0.0.0.0"
            
            logger.info(f"Starting XYQO Backend on {host}:{port}")
            logger.info(f"OpenAI configured: {bool(openai_key)}")
            logger.info("Render deployment - optimized for persistent workers")
            
            # Start uvicorn server with Render-optimized settings
            import uvicorn
            uvicorn.run(
                app, 
                host=host, 
                port=port,
                log_level="info",
                access_log=True,
                workers=1,
                timeout_keep_alive=65,  # Increased for OpenAI processing
                timeout_graceful_shutdown=30,
                loop="asyncio"
            )
        
        except Exception as e:
            logger.error(f"Startup failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            sys.exit(1)
    
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
