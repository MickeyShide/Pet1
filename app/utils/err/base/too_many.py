from starlette import status
from starlette.exceptions import HTTPException


class TooManyRequestsException(HTTPException):
    def __init__(self, detail: str = "too_many_requests_error"):
        super().__init__(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=detail)
