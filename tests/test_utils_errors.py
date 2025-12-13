from app.utils.err.auth import TooManyAttempts
from app.utils.err.base.too_many import TooManyRequestsException


def test_too_many_requests_exception_has_status():
    exc = TooManyRequestsException("limit reached")
    assert exc.status_code == 429
    assert exc.detail == "limit reached"


def test_too_many_attempts_message():
    exc = TooManyAttempts()
    assert "Too many auth attempts" in exc.detail
