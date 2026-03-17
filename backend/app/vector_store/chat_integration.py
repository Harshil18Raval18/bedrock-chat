"""Integration of vector search with chat functionality."""

import logging
from typing import List, Dict, Any, Optional
from app.vector_store.embeddings import EmbeddingsService
from app.vector_store.repository import VectorStoreRepository
from app.repositories.models.conversation import RelatedDocumentModel

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class VectorSearchIntegration:
    """Integrate vector search into chat responses."""

    def __init__(self):
        self.embeddings_service = EmbeddingsService()
        self.repository = VectorStoreRepository()

    def search_relevant_documents(
        self, bot_id: str, query: str, limit: int = 5, threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant documents based on user query.
        
        Args:
            bot_id: Bot ID
            query: User query text
            limit: Maximum number of results
            threshold: Similarity threshold (0-1)
            
        Returns:
            List of relevant document chunks with metadata
        """
        try:
            # Generate embedding for query
            query_embedding = self.embeddings_service.generate_embedding(query)

            # Search similar chunks
            results = self.repository.search_similar_chunks(
                bot_id=bot_id,
                embedding=query_embedding,
                limit=limit,
                threshold=threshold,
            )

            logger.info(f"Found {len(results)} relevant documents for bot: {bot_id}")
            return results

        except Exception as e:
            logger.error(f"Error searching documents: {str(e)}")
            return []

    def format_search_results_for_prompt(
        self, search_results: List[Dict[str, Any]]
    ) -> str:
        """
        Format search results to include in system prompt.
        
        Args:
            search_results: Results from vector search
            
        Returns:
            Formatted string for inclusion in prompt
        """
        if not search_results:
            return ""

        formatted = "\n\n## Retrieved Documents:\n"
        for idx, result in enumerate(search_results, 1):
            formatted += f"\n### Document {idx}: {result['file_name']}\n"
            formatted += f"**Page:** {result.get('page_number', 'N/A')}\n"
            formatted += f"**Similarity:** {result.get('similarity_score', 0):.2%}\n"
            formatted += f"**Content:** {result['chunk_text'][:500]}...\n"
            formatted += f"**Source:** {result['s3_path']}\n"

        return formatted

    def create_related_documents(
        self, search_results: List[Dict[str, Any]]
    ) -> List[RelatedDocumentModel]:
        """
        Convert search results to RelatedDocumentModel for response.
        
        Args:
            search_results: Results from vector search
            
        Returns:
            List of RelatedDocumentModel objects
        """
        related_docs = []

        for result in search_results:
            try:
                doc = RelatedDocumentModel(
                    title=result["file_name"],
                    content=result["chunk_text"],
                    source=result["s3_path"],
                    page_number=result.get("page_number"),
                    similarity_score=result.get("similarity_score", 0),
                )
                related_docs.append(doc)
            except Exception as e:
                logger.error(f"Error creating related document: {str(e)}")
                continue

        return related_docs
