import logging

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def _normalize_errors(data):
    if isinstance(data, dict):
        return data
    if isinstance(data, list):
        return {"non_field_errors": data}
    return {}


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        request = context.get("request")
        safe_data = {}
        if request is not None and hasattr(request, "data") and isinstance(request.data, dict):
            safe_data = {key: ("[redacted]" if "password" in key.lower() else value) for key, value in request.data.items()}
        logger.warning(
            "API request failed",
            extra={
                "path": getattr(request, "path", ""),
                "method": getattr(request, "method", ""),
                "status_code": response.status_code,
                "request_data": safe_data,
                "response_data": response.data,
            },
        )
        if isinstance(exc, ValidationError):
            return Response(
                {
                    "message": "Validation failed",
                    "errors": _normalize_errors(response.data),
                },
                status=response.status_code,
            )

        detail = response.data.get("detail") if isinstance(response.data, dict) else None
        message = detail or "Request failed"
        errors = {}
        if isinstance(response.data, dict) and "detail" not in response.data:
            errors = response.data

        return Response(
            {
                "message": message,
                "errors": errors,
            },
            status=response.status_code,
        )

    request = context.get("request")
    logger.exception(
        "Unhandled API error",
        extra={
            "path": getattr(request, "path", ""),
            "method": getattr(request, "method", ""),
        },
    )
    return Response(
        {
            "message": "An unexpected server error occurred.",
            "errors": {},
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
