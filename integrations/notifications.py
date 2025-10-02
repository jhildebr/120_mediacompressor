import logging
import os
from typing import Dict

import requests

from integrations.database import extract_step_id_from_blob_name


def send_completion_notification(blob_name: str, result: Dict) -> None:
    step_id = extract_step_id_from_blob_name(blob_name)

    payload = {
        "target": "MediaProcessingComplete",
        "arguments": [
            {
                "step_id": step_id,
                "blob_name": blob_name,
                "status": result.get("status"),
                "compressed_url": result.get("output_url"),
                "compression_ratio": result.get("compression_ratio"),
                "processing_time": result.get("processing_time", 0),
            }
        ],
    }

    send_signalr_message(payload)

    webhook_url = os.environ.get("WEBHOOK_URL")
    if webhook_url:
        try:
            response = requests.post(webhook_url, json=payload["arguments"][0], timeout=10)
            logging.info("Webhook notification sent: %s", response.status_code)
        except Exception as exc:  # pragma: no cover - best effort
            logging.warning("Webhook notification failed: %s", str(exc))


def send_signalr_message(payload: Dict) -> None:
    # Placeholder for Azure SignalR REST API integration
    endpoint = os.environ.get("SIGNALR_ENDPOINT")
    if not endpoint:
        logging.info("SIGNALR_ENDPOINT not set; skipping SignalR send")
        return
    # Implement actual SignalR send here when endpoint and auth are available.
    logging.debug("Would send to SignalR at %s: %s", endpoint, payload)


