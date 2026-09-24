
from fastapi import (
    APIRouter,
    HTTPException,
)

from app.core.database import (
    check_database_connection,
)


router = APIRouter(
    prefix="/api/v1/database",
    tags=["database"],
)


@router.get("/status")
def database_status():

    result = (
        check_database_connection()
    )

    if not result.get(
        "connected"
    ):

        raise HTTPException(
            status_code=503,
            detail=result,
        )

    return result
