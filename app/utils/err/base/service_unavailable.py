from starlette import status
from starlette.exceptions import HTTPException


class ServiceUnavailableException(HTTPException):
    def __init__(self, detail: str = "service_unavailable"):
        super().__init__(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)
