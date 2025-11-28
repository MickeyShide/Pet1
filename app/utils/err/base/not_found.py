from starlette import status
from starlette.exceptions import HTTPException


class NotFoundException(HTTPException):
    def __init__(self, detail: str = "not_found_error"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
