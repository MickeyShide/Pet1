from starlette import status
from starlette.exceptions import HTTPException


class ForbiddenException(HTTPException):
    def __init__(self, detail: str = "forbidden error"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)