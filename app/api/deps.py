# app/api/deps.py
from datetime import datetime
from typing import Annotated

from fastapi import Depends, Query
from fastapi.exceptions import RequestValidationError
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt, JWTError
from pydantic import ValidationError

from app.config import settings
from app.schemas.auth import SAccessToken
from app.models.booking import BookingStatus
from app.schemas.booking import SBookingFilters
from app.schemas.timeslot import STimeSlotDateRange, STimeSlotFilters
from app.utils.err.base.forbidden import ForbiddenException
from app.utils.err.base.unauthorized import UnauthorizedException

_http_bearer = HTTPBearer(auto_error=False)
HTTPBearerDepends = Annotated[HTTPAuthorizationCredentials | None, Depends(_http_bearer)]


async def get_token_data(jwt_token: HTTPBearerDepends) -> SAccessToken:
    if jwt_token is None:
        raise UnauthorizedException("Missing access token")
    try:
        payload = jwt.decode(
            jwt_token.credentials,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise UnauthorizedException("Invalid access token")

    try:
        return SAccessToken(**payload)
    except (TypeError, ValueError) as e:
        print(e)
        raise UnauthorizedException("Invalid access token subject")


async def get_admin_token_data(token: SAccessToken = Depends(get_token_data)) -> SAccessToken:
    if token.admin:
        return token
    else:
        raise ForbiddenException("Not allowed")


UserDepends = Annotated[SAccessToken, Depends(get_token_data)]

AdminDepends = Annotated[SAccessToken, Depends(get_admin_token_data)]


def _build_timeslot_date_range(
        date_from: datetime = Query(...),
        date_to: datetime | None = Query(None),
) -> STimeSlotDateRange:
    try:
        return STimeSlotDateRange(date_from=date_from, date_to=date_to)
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from exc


TimeSlotDateRangeDepends = Annotated[STimeSlotDateRange, Depends(_build_timeslot_date_range)]


def _build_booking_filters(
        room_id: int | None = Query(None),
        status: BookingStatus | None = Query(None),
) -> SBookingFilters:
    payload: dict[str, object] = {}
    if room_id is not None:
        payload["room_id"] = room_id
    if status is not None:
        payload["status"] = status
    return SBookingFilters(**payload)


def _build_timeslot_filters(
        start_datetime: datetime | None = Query(None),
        end_datetime: datetime | None = Query(None),
) -> STimeSlotFilters:
    payload: dict[str, object] = {}
    if start_datetime is not None:
        payload["start_datetime"] = start_datetime
    if end_datetime is not None:
        payload["end_datetime"] = end_datetime
    return STimeSlotFilters(**payload)


BookingFiltersDepends = Annotated[SBookingFilters, Depends(_build_booking_filters)]
TimeSlotFiltersDepends = Annotated[STimeSlotFilters, Depends(_build_timeslot_filters)]
