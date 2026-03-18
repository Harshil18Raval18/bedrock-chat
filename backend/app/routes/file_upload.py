"""API routes for file upload and management."""

import logging
import os
from typing import Annotated
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Query
from fastapi.responses import JSONResponse

from app.dependencies import get_current_user
from app.user import User
from app.vector_store.lambda_processor import FileProcessingService
from app.vector_store.repository import VectorStoreRepository
from app.usecases.bot import fetch_bot

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter(tags=["file_upload"])

# Initialize services
file_service = FileProcessingService()
vector_repo = VectorStoreRepository()


@router.post("/bot/{bot_id}/upload-file")
async def upload_file(
    bot_id: str,
    file: UploadFile = File(...),
    user: Annotated[User, Depends(get_current_user)] = None,
) -> JSONResponse:
    """
    Upload a PDF file for a bot.
    File will be stored in S3 and processed for vector embeddings.
    
    Args:
        bot_id: Bot ID
        file: PDF file to upload
        user: Current authenticated user
        
    Returns:
        Upload result with document ID and processing status
    """
    try:
        # Verify bot ownership
        owned, bot = fetch_bot(user, bot_id)
        if not owned:
            raise HTTPException(status_code=403, detail="Not authorized to upload files for this bot")

        # Validate file type
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")

        # Upload to S3
        s3_bucket = os.getenv("LARGE_MESSAGE_BUCKET")
        if not s3_bucket:
            logger.error("LARGE_MESSAGE_BUCKET environment variable not set")
            raise HTTPException(status_code=500, detail="S3 bucket not configured. Please contact administrator.")

        s3_key = f"bot-files/{bot_id}/{file.filename}"
        
        # Read file content
        file_content = await file.read()
        
        # Upload to S3
        import boto3
        s3_client = boto3.client("s3")
        s3_client.put_object(
            Bucket=s3_bucket,
            Key=s3_key,
            Body=file_content,
            ContentType="application/pdf",
        )
        
        logger.info(f"File uploaded to S3: s3://{s3_bucket}/{s3_key}")

        # Process file and store in vector database
        result = file_service.process_file(
            bot_id=bot_id,
            bucket=s3_bucket,
            key=s3_key,
            file_name=file.filename,
        )

        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result.get("error", "Processing failed"))

        return JSONResponse(
            status_code=200,
            content={
                "message": "File uploaded and processed successfully",
                "document_id": result.get("document_id"),
                "chunks_stored": result.get("chunks_stored"),
                "file_name": file.filename,
                "s3_path": result.get("s3_path"),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bot/{bot_id}/files")
async def get_bot_files(
    bot_id: str,
    user: Annotated[User, Depends(get_current_user)] = None,
) -> JSONResponse:
    """
    Get all uploaded files for a bot.
    
    Args:
        bot_id: Bot ID
        user: Current authenticated user
        
    Returns:
        List of documents with metadata
    """
    try:
        # Verify bot access
        owned, bot = fetch_bot(user, bot_id)
        if not owned:
            raise HTTPException(status_code=403, detail="Not authorized to access this bot")

        documents = vector_repo.get_documents_by_bot(bot_id)
        
        return JSONResponse(
            status_code=200,
            content={
                "bot_id": bot_id,
                "documents": [
                    {
                        "id": doc["id"],
                        "file_name": doc["file_name"],
                        "s3_path": doc["s3_path"],
                        "file_size": doc["file_size"],
                        "created_at": doc["created_at"].isoformat() if doc["created_at"] else None,
                    }
                    for doc in documents
                ],
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching bot files: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/bot/{bot_id}/files/{document_id}")
async def delete_file(
    bot_id: str,
    document_id: int,
    user: Annotated[User, Depends(get_current_user)] = None,
) -> JSONResponse:
    """
    Delete an uploaded file and its vector embeddings.
    
    Args:
        bot_id: Bot ID
        document_id: Document ID to delete
        user: Current authenticated user
        
    Returns:
        Deletion confirmation
    """
    try:
        # Verify bot ownership
        owned, bot = fetch_bot(user, bot_id)
        if not owned:
            raise HTTPException(status_code=403, detail="Not authorized to delete files for this bot")

        success = vector_repo.delete_document(document_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Document not found")

        return JSONResponse(
            status_code=200,
            content={"message": "File deleted successfully", "document_id": document_id},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
