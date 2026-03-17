"""PDF processing and text extraction."""

import logging
from typing import List, Tuple
import io
import boto3
from PyPDF2 import PdfReader

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Chunk size for splitting text (tokens approximately)
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50


class PDFProcessor:
    """Process PDF files and extract text chunks."""

    def __init__(self):
        self.s3_client = boto3.client("s3")

    def extract_text_from_pdf(self, bucket: str, key: str) -> List[Tuple[str, int]]:
        """
        Extract text from PDF in S3.
        Returns list of (text_chunk, page_number) tuples.
        """
        try:
            # Download PDF from S3
            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            pdf_content = response["Body"].read()

            # Parse PDF
            pdf_reader = PdfReader(io.BytesIO(pdf_content))
            chunks = []

            for page_num, page in enumerate(pdf_reader.pages, 1):
                text = page.extract_text()
                if text.strip():
                    # Split page text into chunks
                    page_chunks = self._split_text_into_chunks(text)
                    for chunk in page_chunks:
                        chunks.append((chunk, page_num))

            logger.info(f"Extracted {len(chunks)} chunks from PDF: {key}")
            return chunks

        except Exception as e:
            logger.error(f"Error extracting text from PDF {key}: {str(e)}")
            raise

    @staticmethod
    def _split_text_into_chunks(text: str) -> List[str]:
        """Split text into overlapping chunks."""
        words = text.split()
        chunks = []

        for i in range(0, len(words), CHUNK_SIZE - CHUNK_OVERLAP):
            chunk = " ".join(words[i : i + CHUNK_SIZE])
            if chunk.strip():
                chunks.append(chunk)

        return chunks

    def get_pdf_metadata(self, bucket: str, key: str) -> dict:
        """Get PDF metadata from S3."""
        try:
            response = self.s3_client.head_object(Bucket=bucket, Key=key)
            return {
                "file_size": response.get("ContentLength", 0),
                "mime_type": response.get("ContentType", "application/pdf"),
                "last_modified": response.get("LastModified"),
            }
        except Exception as e:
            logger.error(f"Error getting PDF metadata: {str(e)}")
            raise
