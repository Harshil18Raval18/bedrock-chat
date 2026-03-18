"""Database schema initialization for vector store."""

import logging
from app.vector_store.rds_connection import RDSVectorStore

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def init_vector_store_schema():
    """Initialize pgvector extension and create required tables."""
    store = RDSVectorStore()

    try:
        # Enable pgvector extension
        store.execute_update("CREATE EXTENSION IF NOT EXISTS vector")
        logger.info("pgvector extension enabled")

        # Create documents table
        create_documents_table = """
        CREATE TABLE IF NOT EXISTS documents (
            id SERIAL PRIMARY KEY,
            bot_id VARCHAR(255) NOT NULL,
            file_name VARCHAR(500) NOT NULL,
            s3_path VARCHAR(1000) NOT NULL,
            file_size INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        store.execute_update(create_documents_table)
        logger.info("documents table created")

        # Create document chunks table with embeddings
        create_chunks_table = """
        CREATE TABLE IF NOT EXISTS document_chunks (
            id SERIAL PRIMARY KEY,
            document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            chunk_text TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            embedding vector(1536),
            metadata JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        store.execute_update(create_chunks_table)
        logger.info("document_chunks table created")

        # Create indexes
        create_indexes = """
        CREATE INDEX IF NOT EXISTS idx_documents_bot_id ON documents(bot_id);
        CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON document_chunks(document_id);
        CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON document_chunks USING ivfflat (embedding vector_cosine_ops);
        """
        store.execute_update(create_indexes)
        logger.info("Indexes created")

        logger.info("Vector store schema initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize vector store schema: {str(e)}")
        raise
