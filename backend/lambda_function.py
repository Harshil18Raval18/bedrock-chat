"""
Updated Lambda function for processing S3 files and storing in RDS vector database.
This replaces the original lambda.py with vector database integration.
"""

import os
import json
import logging
from datetime import datetime, timezone
from app.vector_store.lambda_processor import FileProcessingService

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s - %(message)s")
logger = logging.getLogger(__name__)

# Initialize service
file_service = FileProcessingService()


def lambda_handler(event, context):
    """
    Lambda handler for processing uploaded PDF files.
    
    Triggered by:
    1. S3 PUT events (direct file upload)
    2. API Gateway (file upload via endpoint)
    
    Environment Variables:
    - BOT_ID: Bot ID for file association
    - RDS_HOST: RDS endpoint
    - RDS_USER: RDS username
    - RDS_PASSWORD: RDS password
    - RDS_DATABASE: RDS database name
    - S3_BUCKET_NAME: S3 bucket for file storage
    """
    try:
        logger.info(f"Lambda invoked with event: {json.dumps(event)}")

        bot_id = os.getenv("BOT_ID") or event.get("bot_id")
        if not bot_id:
            logger.error("BOT_ID not provided")
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "BOT_ID not provided"}),
            }

        results = []

        # Handle S3 events
        if "Records" in event:
            for record in event.get("Records", []):
                try:
                    # Extract S3 information
                    bucket = record["s3"]["bucket"]["name"]
                    key = record["s3"]["object"]["key"]
                    file_name = key.split("/")[-1]

                    logger.info(f"Processing S3 file: s3://{bucket}/{key}")

                    # Process file
                    result = file_service.process_file(bot_id, bucket, key, file_name)
                    results.append(result)

                    logger.info(f"File processing result: {json.dumps(result)}")

                except Exception as e:
                    logger.error(f"Error processing S3 record: {str(e)}")
                    results.append({"status": "error", "error": str(e)})

        # Handle direct API calls
        elif "bucket" in event and "key" in event:
            try:
                bucket = event["bucket"]
                key = event["key"]
                file_name = event.get("file_name", key.split("/")[-1])

                logger.info(f"Processing file from API: s3://{bucket}/{key}")

                result = file_service.process_file(bot_id, bucket, key, file_name)
                results.append(result)

            except Exception as e:
                logger.error(f"Error processing API request: {str(e)}")
                results.append({"status": "error", "error": str(e)})

        else:
            logger.warning("No S3 records or bucket/key in event")

        # Return response
        success_count = sum(1 for r in results if r.get("status") == "success")
        error_count = sum(1 for r in results if r.get("status") == "error")

        return {
            "statusCode": 200 if error_count == 0 else 206,
            "body": json.dumps(
                {
                    "message": "File processing completed",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "processed": len(results),
                    "successful": success_count,
                    "failed": error_count,
                    "results": results,
                }
            ),
        }

    except Exception as e:
        logger.error(f"Lambda handler error: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps(
                {
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            ),
        }
