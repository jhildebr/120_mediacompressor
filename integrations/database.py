import json
import logging
import os
import re
from typing import Dict

import requests


def extract_step_id_from_blob_name(blob_name: str) -> str:
    parts = blob_name.split("-")
    if len(parts) >= 2 and parts[0] == "step":
        return parts[1]

    uuid_pattern = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    match = re.search(uuid_pattern, blob_name, re.IGNORECASE)
    if match:
        return match.group()

    raise ValueError(f"Could not extract step ID from blob name: {blob_name}")


def update_database(blob_name: str, result: Dict) -> None:
    step_id = extract_step_id_from_blob_name(blob_name)

    api_payload = {
        "processing_status": result.get("status", "unknown"),
        "compressed_url": result.get("output_url"),
        "original_size": result.get("original_size"),
        "compressed_size": result.get("compressed_size"),
        "compression_ratio": result.get("compression_ratio"),
    }

    base_url = os.environ.get("SIMPI_API_BASE_URL")
    token = os.environ.get("SIMPI_API_TOKEN")
    if not base_url or not token:
        logging.warning("SIMPI API env vars missing; skipping DB update")
        return

    api_url = f"{base_url}/api/v1/steps/{step_id}/media"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    response = requests.put(api_url, json=api_payload, headers=headers, timeout=20)
    if not response.ok:
        logging.error("Failed to update database: %s", response.text)
        raise RuntimeError("Database update failed")

    logging.info("Successfully updated database for step %s", step_id)


def update_database_error(blob_name: str, error: str) -> None:
    try:
        step_id = extract_step_id_from_blob_name(blob_name)
    except Exception:
        step_id = "unknown"

    payload = {"processing_status": "error", "error": error}
    base_url = os.environ.get("SIMPI_API_BASE_URL")
    token = os.environ.get("SIMPI_API_TOKEN")
    if not base_url or not token:
        logging.warning("SIMPI API env vars missing; skipping error DB update")
        return

    api_url = f"{base_url}/api/v1/steps/{step_id}/media"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    requests.put(api_url, data=json.dumps(payload), headers=headers, timeout=20)


