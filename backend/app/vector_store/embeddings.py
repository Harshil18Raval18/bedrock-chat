"""Bedrock embeddings service for generating vector embeddings."""

import logging
from typing import List
import json
from app.utils import get_bedrock_runtime_client

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Bedrock Titan Embeddings model (cheapest option)
EMBEDDING_MODEL_ID = "amazon.titan-embed-text-v2:0"
EMBEDDING_DIMENSION = 1536


class EmbeddingsService:
    """Service for generating embeddings using Bedrock Titan."""

    def __init__(self):
        self.bedrock_client = get_bedrock_runtime_client()
        self.model_id = EMBEDDING_MODEL_ID

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text chunk."""
        try:
            if not text or not text.strip():
                logger.warning("Empty text provided for embedding")
                return [0.0] * EMBEDDING_DIMENSION

            response = self.bedrock_client.invoke_model(
                modelId=self.model_id,
                contentType="application/json",
                body=json.dumps({"inputText": text}),
            )

            response_body = json.loads(response["body"].read())
            embedding = response_body.get("embedding", [])

            if not embedding:
                logger.warning("Empty embedding returned from Bedrock")
                return [0.0] * EMBEDDING_DIMENSION

            return embedding

        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            raise

    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple text chunks."""
        embeddings = []
        for text in texts:
            try:
                embedding = self.generate_embedding(text)
                embeddings.append(embedding)
            except Exception as e:
                logger.error(f"Error generating embedding for text: {str(e)}")
                # Return zero vector on error to maintain alignment
                embeddings.append([0.0] * EMBEDDING_DIMENSION)

        return embeddings
