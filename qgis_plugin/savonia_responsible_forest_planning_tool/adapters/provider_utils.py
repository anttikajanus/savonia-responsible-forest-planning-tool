"""Helpers for checking QGIS data-provider results."""


def require_provider_success(result, operation, provider=None):
    success = result[0] if isinstance(result, tuple) else result
    if not success:
        detail = ""
        if provider is not None:
            try:
                detail = str(provider.lastError() or "").strip()
            except Exception:
                detail = ""
        message = "Provider rejected {0}.".format(operation)
        if detail:
            message += " Provider error: {0}".format(detail)
        raise IOError(message)
