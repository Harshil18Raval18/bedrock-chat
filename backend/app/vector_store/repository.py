"""Vector store repository for storing and searching documents."""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.vector_store.rds_connection import RDSVectorStore

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class VectorStoreRepository:
    """Repository for vector store operations."""

    def __init__(self):
        self.store = RDSVectorStore()

    def store_document(
        self, bot_id: str, file_name: str, s3_path: str, file_size: int, mime_type: str
    ) -> int:
        """Store document metadata and return document ID."""
        try:
            query = """
            INSERT INTO vector_documents (bot_id, file_name, s3_path, file_size, mime_type)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (bot_id, s3_path) DO UPDATE SET updated_at = CURRENT_TIMESTAMP
            RETURNING id;
            """
            result = self.store.execute_query(
                query, (bot_id, file_name, s3_path, file_size, mime_type), fetch_one=True
            )
            document_id = result["id"]
            logger.info(f"Stored document: {file_name} with ID: {document_id}")
            return document_id

        except Exception as e:
            logger.error(f"Error storing document: {str(e)}")
            raise

    def store_chunks(
        self,
        document_id: int,
        bot_id: str,
        chunks: List[Dict[str, Any]],
    ) -> int:
        """Store document chunks with embeddings."""
        try:
            query = """
            INSERT INTO vector_chunks (document_id, bot_id, chunk_index, chunk_text, embedding, page_number)
            VALUES (%s, %s, %s, %s, %s, %s)
            """

            params_list = [
                (
                    document_id,
                    bot_id,
                    chunk["index"],
                    chunk["text"],
                    chunk["embedding"],
                    chunk.get("page_number"),
                )
                for chunk in chunks
            ]

            rowcount = self.store.execute_batch(query, params_list)
            logger.info(f"Stored {rowcount} chunks for document ID: {document_id}")
            return rowcount

        except Exception as e:
            logger.error(f"Error storing chunks: {str(e)}")
            raise

    def search_similar_chunks(
        self, bot_id: str, embedding: List[float], limit: int = 5, threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Search for similar chunks using vector similarity."""
        try:
            query = """
            SELECT 
                vc.id,
                vc.chunk_text,
                vc.page_number,
                vd.file_name,
                vd.s3_path,
                1 - (vc.embedding <=> %s::vector) as similarity_score
            FROM vector_chunks vc
            JOIN vector_documents vd ON vc.document_id = vd.id
            WHERE vc.bot_id = %s
            AND (1 - (vc.embedding <=> %s::vector)) > %s
            ORDER BY vc.embedding <=> %s::vector
            LIMIT %s;
            """

            embedding_str = "[" + ",".join(map(str, embedding)) + "]"
            results = self.store.execute_query(
                query, (embedding_str, bot_id, embedding_str, threshold, embedding_str, limit)
            )

            logger.info(f"Found {len(results)} similar chunks for bot: {bot_id}")
            return results

        except Exception as e:
            logger.error(f"Error searching similar chunks: {str(e)}")
            raise

    def get_documents_by_bot(self, bot_id: str) -> List[Dict[str, Any]]:
        """Get all documents for a bot."""
        try:
            query = """
            SELECT id, bot_id, file_name, s3_path, file_size, mime_type, created_at
            FROM vector_documents
            WHERE bot_id = %s
            ORDER BY created_at DESC;
            """
            results = self.store.execute_query(query, (bot_id,))
            return results

        except Exception as e:
            logger.error(f"Error fetching documents: {str(e)}")
            raise

    def delete_document(self, document_id: int) -> bool:
        """Delete document and its chunks."""
        try:
            query = "DELETE FROM vector_documents WHERE id = %s;"
            rowcount = self.store.execute_update(query, (document_id,))
            logger.info(f"Deleted document ID: {document_id}")
            return rowcount > 0

        except Exception as e:
            logger.error(f"Error deleting document: {str(e)}")
            raise

    def delete_bot_documents(self, bot_id: str) -> int:
        """Delete all documents for a bot."""
        try:
            query = "DELETE FROM vector_documents WHERE bot_id = %s;"
            rowcount = self.store.execute_update(query, (bot_id,))
            logger.info(f"Deleted {rowcount} documents for bot: {bot_id}")
            return rowcount

        except Exception as e:
            logger.error(f"Error deleting bot documents: {str(e)}")
            raise
