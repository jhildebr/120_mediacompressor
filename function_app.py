import base64
import json
import logging
import os
import time
from datetime import datetime

import azure.functions as func
from azure.storage.queue import QueueServiceClient
from azure.storage.blob import BlobServiceClient

from integrations.database import update_database
from integrations.errors import handle_processing_error
from integrations.notifications import send_completion_notification
from integrations.tracking import (
    create_job_record,
    update_job_status,
    get_job_status,
    delete_job_record,
    get_old_completed_jobs,
)
from integrations.auth import require_auth
from processing.image import process_image
from processing.video import process_video


app = func.FunctionApp()

START_TIME = time.time()


def _determine_priority(file_size_bytes: int) -> str:
    if file_size_bytes < 10 * 1024 * 1024:
        return "high"
    return "normal"


@app.blob_trigger(
    arg_name="myblob",
    path="uploads/{name}",
    connection="AzureWebJobsStorage",
)
def process_media_upload(myblob: func.InputStream) -> None:
    """Triggered when a file is uploaded to the 'uploads' container.

    Creates a processing job and enqueues it for downstream processing.
    """
    try:
        logging.info("=== BLOB TRIGGER STARTED ===")
        logging.info("Blob name: %s", myblob.name)
        logging.info("Blob length: %s", myblob.length)

        # Extract just the blob file name (strip 'uploads/' path if present)
        blob_name = myblob.name.split("/")[-1] if myblob.name else "unknown"
        logging.info("Extracted blob_name: %s", blob_name)

        # Ensure we have a valid length
        file_size = int(myblob.length) if myblob.length else 0
        priority = _determine_priority(file_size)
        file_extension = blob_name.lower().split(".")[-1] if "." in blob_name else "unknown"

        logging.info("File size: %s, Priority: %s, Type: %s", file_size, priority, file_extension)

        # Create job tracking record
        create_job_record(blob_name, file_size, file_extension)

        job = {
            "blob_name": blob_name,
            "file_size": file_size,
            "priority": priority,
            "timestamp": datetime.utcnow().isoformat(),
            "retry_count": 0,
        }

        logging.info("Created job: %s", job)

        queue_client = QueueServiceClient.from_connection_string(
            os.environ["AzureWebJobsStorage"]
        ).get_queue_client("media-processing-queue")

        # Create message without base64 encoding to avoid padding issues
        message_content = json.dumps(job)
        visibility_timeout = 0 if priority == "high" else 30
        queue_client.send_message(message_content, visibility_timeout=visibility_timeout)

        logging.info("Successfully queued processing job for %s", blob_name)
        logging.info("=== BLOB TRIGGER COMPLETED ===")

    except Exception as exc:
        logging.error("Blob trigger failed: %s", str(exc))
        # Update job status to failed
        try:
            blob_name = myblob.name.split("/")[-1] if myblob.name else "unknown"
            update_job_status(blob_name, "failed", error_message=str(exc))
        except Exception:
            pass

        # Send error to poison queue for manual investigation
        try:
            error_job = {
                "blob_name": blob_name,
                "error": str(exc),
                "timestamp": datetime.utcnow().isoformat(),
            }
            queue_client = QueueServiceClient.from_connection_string(
                os.environ["AzureWebJobsStorage"]
            ).get_queue_client("media-processing-poison-queue")
            queue_client.send_message(json.dumps(error_job))
        except Exception as poison_exc:
            logging.error("Failed to send to poison queue: %s", str(poison_exc))


@app.queue_trigger(
    arg_name="msg",
    queue_name="media-processing-queue",
    connection="AzureWebJobsStorage",
)
def process_media_queue(msg: func.QueueMessage) -> None:
    """Process media compression jobs from the queue."""
    job = None
    blob_name = None
    try:
        logging.info("=== QUEUE TRIGGER STARTED ===")
        logging.info("Message ID: %s", msg.id)

        # Try to parse the message body directly first (new format)
        try:
            job = json.loads(msg.get_body().decode())
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Fallback to base64 decoding for backward compatibility
            job = json.loads(base64.b64decode(msg.get_body()).decode())

        logging.info("Processing job: %s", job)

        blob_name = job["blob_name"]
        file_extension = blob_name.lower().split(".")[-1]
        logging.info("Blob name: %s, File extension: %s", blob_name, file_extension)

        # Update status to processing
        update_job_status(blob_name, "processing")

        if file_extension in ["mp4", "mov", "avi", "webm"]:
            logging.info("Processing as VIDEO")
            result = process_video(blob_name, job)
        elif file_extension in ["jpg", "jpeg", "png", "gif", "webp"]:
            logging.info("Processing as IMAGE")
            result = process_image(blob_name, job)
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")

        logging.info("Processing result: %s", result)

        # Update status to completed
        update_job_status(blob_name, "completed", result=result)

        # Update database and notify
        logging.info("Updating database for %s", blob_name)
        update_database(blob_name, result)

        logging.info("Sending completion notification for %s", blob_name)
        send_completion_notification(blob_name, result)

        # Cleanup: Delete original upload blob immediately after successful processing
        try:
            logging.info("Deleting original upload blob: %s", blob_name)
            blob_service = BlobServiceClient.from_connection_string(
                os.environ["AzureWebJobsStorage"]
            )
            blob_service.get_blob_client(container="uploads", blob=blob_name).delete_blob()
            logging.info("Successfully deleted upload blob: %s", blob_name)
        except Exception as cleanup_exc:
            logging.warning("Failed to delete upload blob %s: %s", blob_name, str(cleanup_exc))

        logging.info("=== QUEUE TRIGGER COMPLETED SUCCESSFULLY for %s ===", blob_name)

    except Exception as exc:  # pylint: disable=broad-except
        logging.error("Processing failed: %s", str(exc))

        # Update job status to failed
        if blob_name:
            update_job_status(blob_name, "failed", error_message=str(exc))

        safe_job = job or {"blob_name": "unknown", "retry_count": 0}
        handle_processing_error(msg, safe_job, str(exc))


@app.route(route="health", auth_level=func.AuthLevel.ANONYMOUS)
def health(req: func.HttpRequest) -> func.HttpResponse:  # type: ignore[override]
    """Simple health and build-info endpoint for debugging/UI status."""
    try:
        build_time = "unknown"
        build_time_path = os.path.join(os.environ.get("AzureWebJobsScriptRoot", "."), "BUILD_TIME")
        if os.path.exists(build_time_path):
            with open(build_time_path, "r", encoding="utf-8") as fh:
                build_time = fh.read().strip()

        bundle_version = "unknown"
        host_json_path = os.path.join(os.environ.get("AzureWebJobsScriptRoot", "."), "host.json")
        if os.path.exists(host_json_path):
            try:
                with open(host_json_path, "r", encoding="utf-8") as fh:
                    host_cfg = json.load(fh)
                    bundle_version = (
                        host_cfg.get("extensionBundle", {}).get("version", "unknown")
                    )
            except Exception:  # defensive
                pass

        body = {
            "status": "ok",
            "build_time": build_time,
            "bundle_version": bundle_version,
            "host_uptime_seconds": int(time.time() - START_TIME),
            "functions": [
                "process_media_upload",
                "process_media_queue",
                "test_process",
            ],
        }
        return func.HttpResponse(
            body=json.dumps(body),
            mimetype="application/json",
            status_code=200,
        )
    except Exception as exc:  # pragma: no cover
        return func.HttpResponse(
            body=json.dumps({"status": "error", "error": str(exc)}),
            mimetype="application/json",
            status_code=500,
        )


@app.route(route="status", auth_level=func.AuthLevel.ANONYMOUS, methods=["GET"])
def get_status(req: func.HttpRequest) -> func.HttpResponse:  # type: ignore[override]
    """Get processing status for a blob.

    Query parameters:
        blob_name: Name of the blob to check status for

    Requires authentication via X-API-Key header.
    """
    # Check authentication
    auth_response = require_auth(req)
    if auth_response:
        return auth_response

    try:
        blob_name = req.params.get("blob_name")

        if not blob_name:
            return func.HttpResponse(
                body=json.dumps({"error": "blob_name parameter is required"}),
                mimetype="application/json",
                status_code=400,
            )

        # Get job status from Table Storage
        job_status = get_job_status(blob_name)

        if not job_status:
            return func.HttpResponse(
                body=json.dumps({"error": f"No job found for blob: {blob_name}"}),
                mimetype="application/json",
                status_code=404,
            )

        # Build response
        response = {
            "blob_name": job_status.get("blob_name"),
            "status": job_status.get("status"),
            "file_size": job_status.get("file_size"),
            "file_type": job_status.get("file_type"),
            "created_at": job_status.get("created_at"),
            "updated_at": job_status.get("updated_at"),
        }

        # Add processing details if available
        if job_status.get("processing_started_at"):
            response["processing_started_at"] = job_status.get("processing_started_at")

        # Add completion details if completed
        if job_status.get("status") == "completed":
            response["completed_at"] = job_status.get("completed_at")
            response["processed_blob_name"] = job_status.get("processed_blob_name")
            response["original_size"] = job_status.get("original_size")
            response["compressed_size"] = job_status.get("compressed_size")
            response["compression_ratio"] = job_status.get("compression_ratio")
            response["processing_time"] = job_status.get("processing_time")
            response["output_url"] = job_status.get("output_url")

        # Add error details if failed
        if job_status.get("status") == "failed":
            response["failed_at"] = job_status.get("failed_at")
            response["error_message"] = job_status.get("error_message")

        return func.HttpResponse(
            body=json.dumps(response),
            mimetype="application/json",
            status_code=200,
        )

    except Exception as exc:
        logging.error("Status check failed: %s", str(exc))
        return func.HttpResponse(
            body=json.dumps({"error": str(exc)}),
            mimetype="application/json",
            status_code=500,
        )


@app.route(route="test-process", auth_level=func.AuthLevel.ANONYMOUS, methods=["POST"])
def test_process(req: func.HttpRequest) -> func.HttpResponse:  # type: ignore[override]
    """Test endpoint to process a file directly without using the queue."""
    try:
        req_body = req.get_json()
        blob_name = req_body.get("blob_name")

        if not blob_name:
            return func.HttpResponse(
                body=json.dumps({"error": "blob_name is required"}),
                mimetype="application/json",
                status_code=400,
            )

        logging.info("=== TEST PROCESS STARTED ===")
        logging.info("Blob name: %s", blob_name)

        # Create a mock job
        job = {
            "blob_name": blob_name,
            "file_size": 0,
            "priority": "high",
            "timestamp": datetime.utcnow().isoformat(),
            "retry_count": 0,
        }

        # Determine file type and process
        file_extension = blob_name.lower().split(".")[-1]
        logging.info("File extension: %s", file_extension)

        if file_extension in ["mp4", "mov", "avi", "webm"]:
            logging.info("Processing as VIDEO")
            result = process_video(blob_name, job)
        elif file_extension in ["jpg", "jpeg", "png", "gif", "webp"]:
            logging.info("Processing as IMAGE")
            result = process_image(blob_name, job)
        else:
            return func.HttpResponse(
                body=json.dumps({"error": f"Unsupported file type: {file_extension}"}),
                mimetype="application/json",
                status_code=400,
            )

        logging.info("Processing result: %s", result)

        # Update database and notify
        update_database(blob_name, result)
        send_completion_notification(blob_name, result)

        logging.info("=== TEST PROCESS COMPLETED ===")

        return func.HttpResponse(
            body=json.dumps({
                "status": "success",
                "blob_name": blob_name,
                "result": result,
            }),
            mimetype="application/json",
            status_code=200,
        )

    except Exception as exc:
        logging.error("Test processing failed: %s", str(exc))
        return func.HttpResponse(
            body=json.dumps({"status": "error", "error": str(exc)}),
            mimetype="application/json",
            status_code=500,
        )


@app.timer_trigger(arg_name="timer", schedule="0 */5 * * * *")
def cleanup_old_files(timer: func.TimerRequest) -> None:
    """Cleanup timer that runs every 5 minutes.

    Deletes:
    - Processed files older than 10 minutes
    - Associated job tracking records
    """
    try:
        logging.info("=== CLEANUP TIMER STARTED ===")

        # Get completed jobs older than 10 minutes
        old_jobs = get_old_completed_jobs(minutes_old=10)
        logging.info("Found %d old completed jobs to clean up", len(old_jobs))

        blob_service = BlobServiceClient.from_connection_string(
            os.environ["AzureWebJobsStorage"]
        )

        deleted_count = 0
        error_count = 0

        for job in old_jobs:
            try:
                blob_name = job.get("blob_name")
                processed_blob_name = job.get("processed_blob_name")

                if not processed_blob_name:
                    # Derive from blob_name if not stored
                    processed_blob_name = blob_name.replace("upload-", "processed-")

                # Delete processed blob
                try:
                    processed_client = blob_service.get_blob_client(
                        container="processed", blob=processed_blob_name
                    )
                    processed_client.delete_blob()
                    logging.info("Deleted processed blob: %s", processed_blob_name)
                except Exception as blob_exc:
                    logging.warning(
                        "Failed to delete processed blob %s: %s",
                        processed_blob_name,
                        str(blob_exc)
                    )

                # Delete job tracking record
                delete_job_record(blob_name)

                deleted_count += 1

            except Exception as job_exc:
                logging.error("Error cleaning up job %s: %s", job.get("blob_name"), str(job_exc))
                error_count += 1

        logging.info(
            "=== CLEANUP COMPLETED: %d jobs cleaned, %d errors ===",
            deleted_count,
            error_count
        )

    except Exception as exc:
        logging.error("Cleanup timer failed: %s", str(exc))

