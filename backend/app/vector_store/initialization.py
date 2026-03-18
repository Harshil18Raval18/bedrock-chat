"""Initialization module for vector store on application startup."""

import logging
from app.vector_store.schema import init_vector_store_schema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def initialize_vector_store():
    """Initialize vector store schema on application startup."""
    import os
    
    # Check if vector store is configured
    rds_host = os.getenv("RDS_HOST")
    if not rds_host:
        logger.warning("RDS_HOST not configured, skipping vector store initialization")
        return
    
    try:
        logger.info("Initializing vector store schema...")
        init_vector_store_schema()
        logger.info("Vector store schema initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize vector store: {str(e)}")
        logger.warning("Vector store features will not be available")
        # Don't fail startup, but log the error
        # This allows graceful degradation if vector store is not available
