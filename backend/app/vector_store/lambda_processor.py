"""Lambda handler for processing uploaded files and storing in vector database."""

import os
import json
import logging
from typing import Dict, Any
from app.vector_store.rds_connection import RDSVectorStore
from app.vector_store.embeddings import EmbeddingsService
from app.vector_store.pdf_processor import PDFProcessor
from app.vector_store.repository import VectorStoreRepository

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class FileProcessingService:
    """Service for processing uploaded files and storing in vector database."""

    def __init__(self):
        self.pdf_processor = PDFProcessor()
        self.embeddings_service = EmbeddingsService()
        self.repository = VectorStoreRepository()

    def process_file(
        self, bot_id: str, bucket: str, key: str, file_name: str
    ) -> Dict[str, Any]:
        """
        Process uploaded file and store in vector database.
        
        Args:
            bot_id: Bot ID
            bucket: S3 bucket name
            key: S3 object key
            file_name: Original file name
            
        Returns:
            Processing result with document ID and chunk count
        """
        try:
            logger.info(f"Processing file: {file_name} for bot: {bot_id}")

            # Get file metadata
            metadata = self.pdf_processor.get_pdf_metadata(bucket, key)

            # Store document metadata
            document_id = self.repository.store_document(
                bot_id=bot_id,
                file_name=file_name,
                s3_path=f"s3://{bucket}/{key}",
                file_size=metadata["file_size"],
                mime_type=metadata["mime_type"],
            )

            # Extract text chunks from PDF
            text_chunks = self.pdf_processor.extract_text_from_pdf(bucket, key)

            if not text_chunks:
                logger.warning(f"No text extracted from file: {file_name}")
                return {
                    "status": "warning",
                    "document_id": document_id,
                    "chunks_stored": 0,
                    "message": "No text content found in PDF",
                }

            # Generate embeddings for chunks
            logger.info(f"Generating embeddings for {len(text_chunks)} chunks")
            texts = [chunk[0] for chunk in text_chunks]
            embeddings = self.embeddings_service.generate_embeddings_batch(texts)

            # Prepare chunks with embeddings
            chunks_data = [
                {
                    "index": idx,
                    "text": text_chunks[idx][0],
                    "embedding": embeddings[idx],
                    "page_number": text_chunks[idx][1],
                }
                for idx in range(len(text_chunks))
            ]

            # Store chunks in vector database
            chunks_stored = self.repository.store_chunks(
                document_id=document_id, bot_id=bot_id, chunks=chunks_data
            )

            logger.info(
                f"Successfully processed file: {file_name}. "
                f"Document ID: {document_id}, Chunks: {chunks_stored}"
            )

            return {
                "status": "success",
                "document_id": document_id,
                "chunks_stored": chunks_stored,
                "file_name": file_name,
                "s3_path": f"s3://{bucket}/{key}",
            }

        except Exception as e:
            logger.error(f"Error processing file {file_name}: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "file_name": file_name,
            }


def lambda_handler(event, context):
    """
    Lambda handler for S3 file upload events.
    
    Expected event structure:
    {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "bucket-name"},
                    "object": {"key": "path/to/file.pdf"}
                },
                "eventName": "ObjectCreated:Put"
            }
        ],
        "bot_id": "bot-id"
    }
    """
    try:
        service = FileProcessingService()
        bot_id = os.getenv("BOT_ID") or event.get("bot_id")

        if not bot_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "BOT_ID not provided"}),
            }

        results = []

        # Process each S3 event
        for record in event.get("Records", []):
            try:
                bucket = record["s3"]["bucket"]["name"]
                key = record["s3"]["object"]["key"]
                file_name = key.split("/")[-1]

                result = service.process_file(bot_id, bucket, key, file_name)
                results.append(result)

            except Exception as e:
                logger.error(f"Error processing record: {str(e)}")
                results.append({"status": "error", "error": str(e)})

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": "File processing completed",
                    "results": results,
                }
            ),
        }

    except Exception as e:
        logger.error(f"Lambda handler error: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
        }
