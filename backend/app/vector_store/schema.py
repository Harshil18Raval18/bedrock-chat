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
        CREATE TABLE IF NOT EXISTS vector_documents (
            id SERIAL PRIMARY KEY,
            bot_id VARCHAR(255) NOT NULL,
            file_name VARCHAR(255) NOT NULL,
            s3_path VARCHAR(512) NOT NULL,
            file_size BIGINT,
            mime_type VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(bot_id, s3_path)
        );
        """
        store.execute_update(create_documents_table)
        logger.info("vector_documents table created")

        # Create document chunks table with embeddings
        create_chunks_table = """
        CREATE TABLE IF NOT EXISTS vector_chunks (
            id SERIAL PRIMARY KEY,
            document_id INTEGER NOT NULL REFERENCES vector_documents(id) ON DELETE CASCADE,
            bot_id VARCHAR(255) NOT NULL,
            chunk_index INTEGER NOT NULL,
            chunk_text TEXT NOT NULL,
            embedding vector(1536),
            page_number INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (document_id) REFERENCES vector_documents(id) ON DELETE CASCADE
        );
        """
        store.execute_update(create_chunks_table)
        logger.info("vector_chunks table created")

        # Create index for vector similarity search
        create_vector_index = """
        CREATE INDEX IF NOT EXISTS vector_chunks_embedding_idx 
        ON vector_chunks USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100);
        """
        store.execute_update(create_vector_index)
        logger.info("Vector index created")

        # Create index for bot_id queries
        create_bot_index = """
        CREATE INDEX IF NOT EXISTS vector_chunks_bot_id_idx 
        ON vector_chunks(bot_id);
        """
        store.execute_update(create_bot_index)
        logger.info("Bot ID index created")

        logger.info("Vector store schema initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize vector store schema: {str(e)}")
        raise
