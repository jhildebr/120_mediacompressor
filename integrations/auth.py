"""API authentication utilities."""

import logging
import os
from typing import Optional

import azure.functions as func


def validate_api_key(req: func.HttpRequest) -> tuple[bool, Optional[str]]:
    """Validate API key from request headers.

    Args:
        req: Azure Function HTTP request

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Get expected API key from environment
    expected_api_key = os.environ.get("API_KEY", "")

    if not expected_api_key:
        logging.warning("API_KEY environment variable not set - authentication disabled")
        return True, None

    # Check for API key in headers
    api_key = req.headers.get("X-API-Key") or req.headers.get("Authorization")

    # Handle Bearer token format
    if api_key and api_key.startswith("Bearer "):
        api_key = api_key[7:]  # Remove "Bearer " prefix

    if not api_key:
        return False, "Missing API key. Provide X-API-Key header or Authorization: Bearer <key>"

    if api_key != expected_api_key:
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
