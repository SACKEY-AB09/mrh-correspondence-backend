from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status as http_status


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        # Already a handled DRF exception (ValidationError, PermissionDenied, etc.)
        # — make sure the shape is consistent.
        
        return response

    # Anything else is an unhandled exception that would otherwise become an HTML 500 page.
    return Response(
        {"detail": "An unexpected server error occurred. Please try again or contact support."},
        status=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
    )