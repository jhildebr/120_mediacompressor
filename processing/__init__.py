import os
from datetime import datetime, timedelta
from typing import Tuple

from azure.storage.blob import (
    BlobServiceClient,
    BlobSasPermissions,
    generate_blob_sas,
)


def _parse_connection_string(connection_string: str) -> dict:
    """Parse Azure Storage connection string into a dictionary."""
    parts = connection_string.split(";")
    kv_pairs = [p for p in parts if p]
    result: dict = {}
    for pair in kv_pairs:
        if "=" in pair:
            key, value = pair.split("=", 1)
            result[key] = value
    return result


def _get_account_info_from_connection_string(connection_string: str) -> Tuple[str, str]:
    """Extract account name and key from the connection string.

    Raises a ValueError if either value is missing.
    """
    parsed = _parse_connection_string(connection_string)
    account_name = parsed.get("AccountName")
    account_key = parsed.get("AccountKey")
    if not account_name or not account_key:
        raise ValueError("Connection string must include AccountName and AccountKey")
    return account_name, account_key


def _get_blob_service_client() -> BlobServiceClient:
    connection_string = os.environ["AzureWebJobsStorage"]
    return BlobServiceClient.from_connection_string(connection_string)


def generate_processed_blob_sas_url(blob_name: str, expiry_minutes: int = 60) -> str:
    """Generate a time-limited SAS URL for a blob in the 'processed' container.

    This uses the Azure Function's `AzureWebJobsStorage` connection string so that
    no public access is required on the storage account or container.
    """
    connection_string = os.environ["AzureWebJobsStorage"]
    account_name, account_key = _get_account_info_from_connection_string(connection_string)

    blob_service_client = _get_blob_service_client()
    blob_client = blob_service_client.get_blob_client(container="processed", blob=blob_name)

    expires_on = datetime.utcnow() + timedelta(minutes=expiry_minutes)
    permissions = BlobSasPermissions(read=True)

    sas = generate_blob_sas(
        account_name=account_name,
        container_name="processed",
        blob_name=blob_name,
        account_key=account_key,
        permission=permissions,
        expiry=expires_on,
    )

    return f"{blob_client.url}?{sas}"



