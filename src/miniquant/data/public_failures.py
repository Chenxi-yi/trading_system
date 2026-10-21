"""Only nonsecret failure types and numeric codes; no exception messages."""
from urllib.error import HTTPError, URLError


def failure_record(exc):
    result = dict(error_type=type(exc).__name__)
    if isinstance(exc, HTTPError):
        result['http_status'] = int(exc.code)
        result['access_block'] = exc.code in (403, 451)
    elif isinstance(exc, URLError):
        reason = exc.reason
        result['reason_type'] = type(reason).__name__
        if isinstance(getattr(reason, 'errno', None), int):
            result['reason_errno'] = reason.errno
    elif isinstance(getattr(exc, 'errno', None), int):
        result['errno'] = exc.errno
    return result
