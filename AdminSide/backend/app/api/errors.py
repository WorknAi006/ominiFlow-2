"""Shared mapping of service exceptions to HTTP errors for routers."""
import logging
from collections.abc import Iterator, Mapping
from contextlib import contextmanager

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


@contextmanager
def service_errors(mapping: Mapping[type[Exception], int]) -> Iterator[None]:
    """
    Translate mapped service exceptions (most specific first) into
    HTTPException with the exception's (already safe) message. Database
    errors become a generic 503 without internal details.
    """

    try:
        yield

    except tuple(mapping) as exc:
        status_code = next(
            code for error_type, code in mapping.items() if isinstance(exc, error_type)
        )
        raise HTTPException(status_code=status_code, detail=str(exc))

    except SQLAlchemyError:
        logger.exception("Database error.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable.",
        )
