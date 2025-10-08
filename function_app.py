import json
import logging
import os
import threading
import time
from datetime import datetime

import azure.functions as func
from azure.storage.blob import BlobServiceClient

from integrations.database import update_database
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
            "endpoints": [
                "POST /api/process",
                "POST /api/upload",
                "GET /api/status",
                "GET /api/health",
                "GET /api/version",
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


@app.route(route="version", auth_level=func.AuthLevel.ANONYMOUS)
def version_check(req: func.HttpRequest) -> func.HttpResponse:  # type: ignore[override]
    """Version endpoint for deployment verification.

    Returns commit SHA and instance ID to verify all EP1 workers
    are running the same code version.
    """
    try:
        # Get commit SHA from environment (set during deployment)
        commit_sha = os.environ.get("COMMIT_SHA", "unknown")

        # Get instance ID to verify we're hitting different workers
        instance_id = os.environ.get("WEBSITE_INSTANCE_ID", "unknown")

        # Get hostname to further identify the instance
        hostname = os.environ.get("COMPUTERNAME", os.environ.get("HOSTNAME", "unknown"))

        body = {
            "version": commit_sha,
            "instance": instance_id,
            "hostname": hostname,
            "uptime_seconds": int(time.time() - START_TIME),
            "timestamp": datetime.utcnow().isoformat(),
        }

        return func.HttpResponse(
            body=json.dumps(body),
            mimetype="application/json",
            status_code=200,
        )
    except Exception as exc:
        return func.HttpResponse(
            body=json.dumps({"error": str(exc)}),
            mimetype="application/json",
            status_code=500,
        )


@app.route(route="wherefrom", auth_level=func.AuthLevel.ANONYMOUS)
def wherefrom(req: func.HttpRequest) -> func.HttpResponse:  # type: ignore[override]
    """Diagnostic endpoint to verify module import locations.

    Shows where Python worker is importing modules from to identify
    potential shadowing by Azure Files mount.
    """
    try:
        import sys
        from integrations import database

        info = {
            "instance": os.environ.get("WEBSITE_INSTANCE_ID", "unknown"),
            "script_root": os.environ.get("AzureWebJobsScriptRoot", "unknown"),
            "cwd": os.getcwd(),
            "sys_path": sys.path,
            "database_file": getattr(database, "__file__", None),
            "database_mtime": os.path.getmtime(database.__file__) if hasattr(database, "__file__") and database.__file__ else None,
            "timestamp": time.time(),
        }

        return func.HttpResponse(
            body=json.dumps(info),
            mimetype="application/json",
            status_code=200,
        )
    except Exception as exc:
        return func.HttpResponse(
            body=json.dumps({"error": str(exc)}),
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


@app.route(route="process", auth_level=func.AuthLevel.ANONYMOUS, methods=["POST"])
def process_media(req: func.HttpRequest) -> func.HttpResponse:  # type: ignore[override]
    """Main processing endpoint - call this after uploading blob to storage.

    POST /api/process
    Body: {"blob_name": "upload-123.png"}
    """
    blob_name = None
    try:
        req_body = req.get_json()
        blob_name = req_body.get("blob_name")

        if not blob_name:
            return func.HttpResponse(
                body=json.dumps({"error": "blob_name is required"}),
                mimetype="application/json",
                status_code=400,
            )

        logging.info("=== PROCESSING STARTED ===")
        logging.info("Blob name: %s", blob_name)

        # Get blob metadata for file size
        try:
            blob_service = BlobServiceClient.from_connection_string(
                os.environ["AzureWebJobsStorage"]
            )
            blob_client = blob_service.get_blob_client(container="uploads", blob=blob_name)
            blob_properties = blob_client.get_blob_properties()
            file_size = blob_properties.size
        except Exception:
            file_size = 0

        # Determine file type
        file_extension = blob_name.lower().split(".")[-1] if "." in blob_name else "unknown"
        logging.info("File size: %s, Type: %s", file_size, file_extension)

        # Create job tracking record
        create_job_record(blob_name, file_size, file_extension)

        # Update status to processing
        update_job_status(blob_name, "processing")

        # Process based on file type
        if file_extension in ["mp4", "mov", "avi", "webm"]:
            logging.info("Processing as VIDEO")
            result = process_video(blob_name, {"blob_name": blob_name, "file_size": file_size})
        elif file_extension in ["jpg", "jpeg", "png", "gif", "webp"]:
            logging.info("Processing as IMAGE")
            result = process_image(blob_name, {"blob_name": blob_name, "file_size": file_size})
        else:
            update_job_status(blob_name, "failed", error_message=f"Unsupported file type: {file_extension}")
            return func.HttpResponse(
                body=json.dumps({"error": f"Unsupported file type: {file_extension}"}),
                mimetype="application/json",
                status_code=400,
            )

        logging.info("Processing result: %s", result)

        # Update status to completed
        update_job_status(blob_name, "completed", result=result)

        # Update database and notify
        update_database(blob_name, result)
        send_completion_notification(blob_name, result)

        # Cleanup: Delete original upload blob
        try:
            blob_client.delete_blob()
            logging.info("Deleted upload blob: %s", blob_name)
        except Exception as cleanup_exc:
            logging.warning("Failed to delete upload blob: %s", str(cleanup_exc))

        logging.info("=== PROCESSING COMPLETED ===")

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
        logging.error("Processing failed: %s", str(exc))
        # Update job status to failed
        if blob_name:
            try:
                update_job_status(blob_name, "failed", error_message=str(exc))
            except Exception:
                pass
        return func.HttpResponse(
            body=json.dumps({"status": "error", "error": str(exc)}),
            mimetype="application/json",
            status_code=500,
        )


@app.route(route="upload", auth_level=func.AuthLevel.ANONYMOUS, methods=["POST", "OPTIONS"])
def upload_and_process(req: func.HttpRequest) -> func.HttpResponse:  # type: ignore[override]
    """Accept file upload, compress it, and return compressed file data.

    INTERIM ENDPOINT FOR TESTING - Not for production use.
    This endpoint accepts direct file uploads and returns the compressed file.

    POST /api/upload
    Content-Type: multipart/form-data
    Body: file field with file data

    Returns: Compressed file as binary blob
    """
    # Handle CORS preflight
    if req.method == "OPTIONS":
        return func.HttpResponse(
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
                "Access-Control-Expose-Headers": "X-Original-Size, X-Compressed-Size, X-Compression-Ratio, X-Processing-Time",
            }
        )

    blob_name = None
    blob_client = None

    try:
        # Get uploaded file from multipart form data
        files = req.files
        if not files or 'file' not in files:
            return func.HttpResponse(
                body=json.dumps({"error": "No file provided. Use 'file' field in multipart form data."}),
                mimetype="application/json",
                status_code=400,
            )

        file_data = files['file']
        original_filename = file_data.filename

        logging.info("=== UPLOAD AND PROCESS STARTED ===")
        logging.info("Original filename: %s", original_filename)

        # Validate file type
        file_extension = original_filename.lower().split(".")[-1] if "." in original_filename else "unknown"

        allowed_extensions = ["mp4", "mov", "avi", "webm", "flv", "wmv", "jpg", "jpeg", "png", "gif", "bmp", "webp"]
        if file_extension not in allowed_extensions:
            return func.HttpResponse(
                body=json.dumps({"error": f"Unsupported file type: {file_extension}. Supported: {', '.join(allowed_extensions)}"}),
                mimetype="application/json",
                status_code=400,
            )

        # Generate unique blob name
        timestamp = int(time.time() * 1000)
        blob_name = f"upload-{timestamp}.{file_extension}"

        logging.info("Generated blob name: %s", blob_name)

        # Upload file to Azure Blob Storage
        blob_service = BlobServiceClient.from_connection_string(
            os.environ["AzureWebJobsStorage"]
        )
        blob_client = blob_service.get_blob_client(container="uploads", blob=blob_name)

        # Read file data
        file_content = file_data.stream.read()
        file_size = len(file_content)

        logging.info("File size: %s bytes", file_size)

        # Validate file size (max 100MB)
        max_size = 100 * 1024 * 1024  # 100MB
        if file_size > max_size:
            return func.HttpResponse(
                body=json.dumps({"error": "File too large. Maximum size is 100MB."}),
                mimetype="application/json",
                status_code=400,
            )

        # Upload to blob storage
        blob_client.upload_blob(file_content, overwrite=True)
        logging.info("Uploaded to Azure Storage: %s", blob_name)

        # Create job tracking record
        create_job_record(blob_name, file_size, file_extension)
        update_job_status(blob_name, "processing")

        # Process based on file type
        if file_extension in ["mp4", "mov", "avi", "webm", "flv", "wmv"]:
            logging.info("Processing as VIDEO")
            result = process_video(blob_name, {"blob_name": blob_name, "file_size": file_size})
        elif file_extension in ["jpg", "jpeg", "png", "gif", "bmp", "webp"]:
            logging.info("Processing as IMAGE")
            result = process_image(blob_name, {"blob_name": blob_name, "file_size": file_size})
        else:
            update_job_status(blob_name, "failed", error_message=f"Unsupported file type: {file_extension}")
            return func.HttpResponse(
                body=json.dumps({"error": f"Unsupported file type: {file_extension}"}),
                mimetype="application/json",
                status_code=400,
            )

        logging.info("Processing result: %s", result)

        # Update status to completed
        update_job_status(blob_name, "completed", result=result)

        # Get processed blob URL
        output_url = result.get("output_url")
        processed_blob_name = blob_name.replace("upload-", "processed-")

        # For videos, change extension to .mp4
        if file_extension in ["mov", "avi", "webm", "flv", "wmv"]:
            processed_blob_name = processed_blob_name.rsplit(".", 1)[0] + ".mp4"
        # For images, change to .webp
        elif file_extension in ["jpg", "jpeg", "png", "gif", "bmp"]:
            processed_blob_name = processed_blob_name.rsplit(".", 1)[0] + ".webp"

        logging.info("Downloading processed file: %s", processed_blob_name)

        # Download compressed file from processed container
        processed_blob_client = blob_service.get_blob_client(
            container="processed",
            blob=processed_blob_name
        )
        compressed_data = processed_blob_client.download_blob().readall()

        logging.info("Compressed file size: %s bytes (ratio: %.2f%%)",
                    len(compressed_data),
                    result.get("compression_ratio", 0) * 100)

        # Cleanup: Delete upload blob
        try:
            blob_client.delete_blob()
            logging.info("Deleted upload blob: %s", blob_name)
        except Exception as cleanup_exc:
            logging.warning("Failed to delete upload blob: %s", str(cleanup_exc))

        logging.info("=== UPLOAD AND PROCESS COMPLETED ===")

        # Determine content type for response
        if file_extension in ["mp4", "mov", "avi", "webm", "flv", "wmv"]:
            content_type = "video/mp4"
            output_filename = original_filename.rsplit(".", 1)[0] + ".mp4"
        else:
            content_type = "image/webp"
            output_filename = original_filename.rsplit(".", 1)[0] + ".webp"

        # Return compressed file as binary response
        return func.HttpResponse(
            body=compressed_data,
            mimetype=content_type,
            status_code=200,
            headers={
                "Content-Disposition": f'attachment; filename="{output_filename}"',
                "X-Original-Size": str(file_size),
                "X-Compressed-Size": str(len(compressed_data)),
                "X-Compression-Ratio": str(result.get("compression_ratio", 0)),
                "X-Processing-Time": str(result.get("processing_time", 0)),
                # CORS headers to expose custom headers to browser
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Expose-Headers": "X-Original-Size, X-Compressed-Size, X-Compression-Ratio, X-Processing-Time",
            }
        )

    except Exception as exc:
        logging.error("Upload and process failed: %s", str(exc))

        # Cleanup upload blob on error
        if blob_name and blob_client:
            try:
                blob_client.delete_blob()
                logging.info("Cleaned up upload blob after error: %s", blob_name)
            except Exception:
                pass

        # Update job status to failed
        if blob_name:
            try:
                update_job_status(blob_name, "failed", error_message=str(exc))
            except Exception:
                pass

        return func.HttpResponse(
            body=json.dumps({"status": "error", "error": str(exc)}),
            mimetype="application/json",
            status_code=500,
        )


def cleanup_old_files() -> None:
    """Cleanup function that deletes processed files older than 10 minutes.

    Runs in background thread every 5 minutes.
    """
    try:
        logging.info("=== CLEANUP STARTED ===")

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
        logging.error("Cleanup failed: %s", str(exc))


def cleanup_worker():
    """Background worker that runs cleanup every 5 minutes."""
    while True:
        try:
            time.sleep(300)  # 5 minutes
            cleanup_old_files()
        except Exception as exc:
            logging.error("Cleanup worker error: %s", str(exc))


# Start cleanup worker in background thread
cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
cleanup_thread.start()
logging.info("Background cleanup worker started")

