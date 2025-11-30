from starlette import status
from starlette.exceptions import HTTPException


class UnauthorizedException(HTTPException):
    def __init__(self, detail: str = "unauthorized_error"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)
