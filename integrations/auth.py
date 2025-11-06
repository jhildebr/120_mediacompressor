"""API authentication utilities."""

import logging
import os
from typing import Optional

import azure.functions as func


def validate_api_key(req: func.HttpRequest) -> tuple[bool, Optional[str]]:
    """Validate API key from request headers.

    Supports multiple API keys from environment variables:
    - COMPRESSION_API_KEY_DEV: Development environment key
    - COMPRESSION_API_KEY_PROD: Production environment key

    Args:
        req: Azure Function HTTP request

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Get valid API keys from environment (support multiple keys)
    valid_keys = []

    # Compression-specific keys
    dev_key = os.environ.get("COMPRESSION_API_KEY_DEV", "")
    prod_key = os.environ.get("COMPRESSION_API_KEY_PROD", "")

    if dev_key:
        valid_keys.append(dev_key)
    if prod_key:
        valid_keys.append(prod_key)

    if not valid_keys:
        logging.warning("No API keys configured - authentication disabled")
        return True, None

    # Check for API key in headers
    api_key = req.headers.get("X-Api-Key") or req.headers.get("X-API-Key") or req.headers.get("Authorization")

    # Handle Bearer token format
    if api_key and api_key.startswith("Bearer "):
        api_key = api_key[7:]  # Remove "Bearer " prefix

    if not api_key:
        return False, "Missing API key. Provide X-Api-Key header or Authorization: Bearer <key>"

    if api_key not in valid_keys:
        logging.warning("Invalid API key provided")
        return False, "Invalid API key"

    return True, None


def require_auth(req: func.HttpRequest) -> Optional[func.HttpResponse]:
    """Decorator-style function to require authentication.

    Args:
        req: Azure Function HTTP request

    Returns:
        HttpResponse with 401 if auth fails, None if auth succeeds
    """
    is_valid, error_message = validate_api_key(req)

    if not is_valid:
        return func.HttpResponse(
            body=f'{{"error": "{error_message}"}}',
            mimetype="application/json",
            status_code=401
        )

    return None
