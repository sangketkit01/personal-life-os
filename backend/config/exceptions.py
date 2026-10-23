from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    """
    Custom exception handler to guarantee a consistent 'detail' field
    across all validation and runtime errors for client-side consumption.
    """
    response = exception_handler(exc, context)

    if response is not None and isinstance(response.data, dict):
        if 'detail' not in response.data:
            # Generate a helpful top-level detail string from field errors
            messages = []
            for field, errors in response.data.items():
                if isinstance(errors, list) and len(errors) > 0:
                    messages.append(f"{field}: {errors[0]}")
                elif isinstance(errors, dict):
                    messages.append(f"{field}: {errors}")
                else:
                    messages.append(f"{field}: {errors}")
            response.data['detail'] = "; ".join(messages) if messages else "An error occurred."

    return response
