from starlette import status
from starlette.exceptions import HTTPException


class ConflictException(HTTPException):
    def __init__(self, detail: str = "conflict_exception"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)
