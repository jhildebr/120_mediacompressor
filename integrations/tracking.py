"""Job tracking using Azure Table Storage."""

import logging
import os
from datetime import datetime, timezone
from typing import Dict, Optional

from azure.data.tables import TableServiceClient, TableClient
from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError


TABLE_NAME = "processingjobs"


def _get_table_client() -> TableClient:
    """Get Azure Table Storage client."""
    connection_string = os.environ["AzureWebJobsStorage"]
    table_service = TableServiceClient.from_connection_string(connection_string)

    # Ensure table exists
    try:
        table_service.create_table(TABLE_NAME)
    except ResourceExistsError:
        pass

    return table_service.get_table_client(TABLE_NAME)


def create_job_record(blob_name: str, file_size: int, file_type: str) -> Dict:
    """Create a new job tracking record.

    Args:
        blob_name: Name of the blob in uploads container
        file_size: Size of the uploaded file in bytes
        file_type: File extension (mp4, jpg, etc.)

    Returns:
        Dict with job information
    """
    table_client = _get_table_client()

    # Use blob_name as both PartitionKey and RowKey for simple lookups
    entity = {
        "PartitionKey": "jobs",
        "RowKey": blob_name,
        "blob_name": blob_name,
        "status": "queued",
        "file_size": file_size,
        "file_type": file_type,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        table_client.create_entity(entity)
        logging.info("Created job record for %s", blob_name)
    except ResourceExistsError:
        logging.warning("Job record already exists for %s", blob_name)

    return entity


def update_job_status(
    blob_name: str,
    status: str,
    result: Optional[Dict] = None,
    error_message: Optional[str] = None
) -> None:
    """Update job status and metadata.

    Args:
        blob_name: Name of the blob
        status: New status (queued, processing, completed, failed)
        result: Processing result dict (if completed)
        error_message: Error message (if failed)
    """
    table_client = _get_table_client()

    try:
        entity = table_client.get_entity(partition_key="jobs", row_key=blob_name)

        entity["status"] = status
        entity["updated_at"] = datetime.now(timezone.utc).isoformat()

        if status == "processing":
            entity["processing_started_at"] = datetime.now(timezone.utc).isoformat()

        if status == "completed" and result:
            entity["completed_at"] = datetime.now(timezone.utc).isoformat()
            entity["original_size"] = result.get("original_size", 0)
            entity["compressed_size"] = result.get("compressed_size", 0)
            entity["compression_ratio"] = result.get("compression_ratio", 0.0)
            entity["processing_time"] = result.get("processing_time", 0.0)
            entity["output_url"] = result.get("output_url", "")
            entity["processed_blob_name"] = blob_name.replace("upload-", "processed-")

        if status == "failed" and error_message:
            entity["error_message"] = error_message
            entity["failed_at"] = datetime.now(timezone.utc).isoformat()

        table_client.update_entity(entity, mode="replace")
        logging.info("Updated job status for %s to %s", blob_name, status)

    except ResourceNotFoundError:
        logging.error("Job record not found for %s", blob_name)


def get_job_status(blob_name: str) -> Optional[Dict]:
    """Get job status and metadata.

    Args:
        blob_name: Name of the blob

    Returns:
        Dict with job information or None if not found
    """
    table_client = _get_table_client()

    try:
        entity = table_client.get_entity(partition_key="jobs", row_key=blob_name)
        return dict(entity)
    except ResourceNotFoundError:
        logging.warning("Job record not found for %s", blob_name)
        return None


def delete_job_record(blob_name: str) -> None:
    """Delete a job tracking record.

    Args:
        blob_name: Name of the blob
    """
    table_client = _get_table_client()

    try:
        table_client.delete_entity(partition_key="jobs", row_key=blob_name)
        logging.info("Deleted job record for %s", blob_name)
    except ResourceNotFoundError:
        logging.warning("Job record not found for deletion: %s", blob_name)


def get_old_completed_jobs(minutes_old: int = 10) -> list:
    """Get completed jobs older than specified minutes.

    Args:
        minutes_old: Age threshold in minutes

    Returns:
        List of job entities
    """
    table_client = _get_table_client()

    from datetime import timedelta
    threshold = datetime.now(timezone.utc) - timedelta(minutes=minutes_old)
    threshold_str = threshold.isoformat()

    # Query for completed jobs older than threshold
    query_filter = f"PartitionKey eq 'jobs' and status eq 'completed' and completed_at lt '{threshold_str}'"

    try:
        entities = table_client.query_entities(query_filter)
        return list(entities)
    except Exception as e:
        logging.error("Error querying old jobs: %s", str(e))
        return []
