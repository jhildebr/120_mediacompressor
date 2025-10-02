import base64
import json
import logging
import os
from datetime import datetime

import azure.functions as func
from azure.storage.queue import QueueClient

from integrations.database import update_database
from integrations.errors import handle_processing_error
from integrations.notifications import send_completion_notification
from processing.image import process_image
from processing.video import process_video


app = func.FunctionApp()


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
    logging.info("Processing blob: %s, size=%s", myblob.name, myblob.length)

    # Extract just the blob file name (strip 'uploads/' path if present)
    blob_name = myblob.name.split("/")[-1]

    priority = _determine_priority(myblob.length)

    job = {
        "blob_name": blob_name,
        "file_size": int(myblob.length),
        "priority": priority,
        "timestamp": datetime.utcnow().isoformat(),
        "retry_count": 0,
    }

    queue_client = QueueClient.from_connection_string(
        os.environ["AzureWebJobsStorage"], "media-processing-queue"
    )

    message = base64.b64encode(json.dumps(job).encode()).decode()
    visibility_timeout = 0 if priority == "high" else 30
    queue_client.send_message(message, visibility_timeout=visibility_timeout)

    logging.info("Queued processing job for %s", blob_name)


@app.queue_trigger(
    arg_name="msg",
    queue_name="media-processing-queue",
    connection="AzureWebJobsStorage",
)
def process_media_queue(msg: func.QueueMessage) -> None:
    """Process media compression jobs from the queue."""
    job = None
    try:
        job = json.loads(base64.b64decode(msg.get_body()).decode())
        logging.info("Processing job: %s", job)

        blob_name: str = job["blob_name"]
        file_extension = blob_name.lower().split(".")[-1]

        if file_extension in ["mp4", "mov", "avi"]:
            result = process_video(blob_name, job)
        elif file_extension in ["jpg", "jpeg", "png", "gif", "webm"]:
            result = process_image(blob_name, job)
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")

        # Update database and notify
        update_database(blob_name, result)
        send_completion_notification(blob_name, result)

        logging.info("Completed processing for %s", blob_name)

    except Exception as exc:  # pylint: disable=broad-except
        logging.error("Processing failed: %s", str(exc))
        safe_job = job or {"blob_name": "unknown", "retry_count": 0}
        handle_processing_error(msg, safe_job, str(exc))


