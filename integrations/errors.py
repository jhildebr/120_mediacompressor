import base64
import json
import logging
import os
from typing import Dict

import azure.functions as func
from azure.storage.queue import QueueClient

from integrations.database import update_database_error


def handle_processing_error(msg: func.QueueMessage, job: Dict, error: str) -> None:
    job["retry_count"] = int(job.get("retry_count", 0)) + 1
    job["last_error"] = error

    max_retries = int(os.environ.get("MAX_RETRY_ATTEMPTS", "3"))

    if job["retry_count"] < max_retries:
        # Exponential backoff in seconds: 2, 4, 8 minutes
        delay = 2 ** job["retry_count"] * 60

        queue_client = QueueClient.from_connection_string(
            os.environ["AzureWebJobsStorage"], "media-processing-queue"
        )

        message = base64.b64encode(json.dumps(job).encode()).decode()
        queue_client.send_message(message, visibility_timeout=delay)
        logging.info("Requeued job %s for retry %s", job.get("blob_name"), job["retry_count"])
        return

    # Max retries reached: send to poison queue and update DB
    send_to_poison_queue(job, error)
    update_database_error(job.get("blob_name", "unknown"), error)


def send_to_poison_queue(job: Dict, error: str) -> None:
    poison_job = {**job, "final_error": error}
    queue_client = QueueClient.from_connection_string(
        os.environ["AzureWebJobsStorage"], "media-processing-poison-queue"
    )
    message = base64.b64encode(json.dumps(poison_job).encode()).decode()
    queue_client.send_message(message)


