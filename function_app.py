import base64
import json
import logging
import os
import time
from datetime import datetime

import azure.functions as func
from azure.storage.queue import QueueServiceClient

from integrations.database import update_database
from integrations.errors import handle_processing_error
from integrations.notifications import send_completion_notification
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
        logging.info("Blob type: %s", type(myblob))
        logging.info("Blob attributes: %s", dir(myblob))

        # Extract just the blob file name (strip 'uploads/' path if present)
        blob_name = myblob.name.split("/")[-1] if myblob.name else "unknown"
        logging.info("Extracted blob_name: %s", blob_name)

        # Ensure we have a valid length
        file_size = int(myblob.length) if myblob.length else 0
        priority = _determine_priority(file_size)
        logging.info("File size: %s, Priority: %s", file_size, priority)

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
        # Send error to poison queue for manual investigation
        try:
            error_job = {
                "blob_name": myblob.name.split("/")[-1] if myblob.name else "unknown",
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
    try:
        logging.info("=== QUEUE TRIGGER STARTED ===")
        logging.info("Message ID: %s", msg.id)
        logging.info("Message content: %s", msg.get_body())
        
        # Try to parse the message body directly first (new format)
        try:
            job = json.loads(msg.get_body().decode())
            logging.info("Parsed job (direct): %s", job)
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Fallback to base64 decoding for backward compatibility
            job = json.loads(base64.b64decode(msg.get_body()).decode())
            logging.info("Parsed job (base64): %s", job)
        
        logging.info("Processing job: %s", job)

        blob_name: str = job["blob_name"]
        file_extension = blob_name.lower().split(".")[-1]
        logging.info("Blob name: %s, File extension: %s", blob_name, file_extension)

        if file_extension in ["mp4", "mov", "avi", "webm"]:
            logging.info("Processing as VIDEO")
            result = process_video(blob_name, job)
        elif file_extension in ["jpg", "jpeg", "png", "gif", "webp"]:
            logging.info("Processing as IMAGE")
            result = process_image(blob_name, job)
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")

        logging.info("Processing result: %s", result)

        # Update database and notify
        logging.info("Updating database for %s", blob_name)
        update_database(blob_name, result)
        
        logging.info("Sending completion notification for %s", blob_name)
        send_completion_notification(blob_name, result)

        logging.info("=== QUEUE TRIGGER COMPLETED SUCCESSFULLY for %s ===", blob_name)

    except Exception as exc:  # pylint: disable=broad-except
        logging.error("Processing failed: %s", str(exc))
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

