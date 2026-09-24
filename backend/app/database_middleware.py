
import json

from fastapi import (
    Request,
    Response,
)

from app.services.database_persistence import (
    persist_screening_payload,
)


TARGET_PATHS = {
    "/api/v1/screen",
    "/api/v1/batch-screen",
}


async def _persist_response(
    response,
):

    body = b""

    async for chunk in response.body_iterator:
        body += chunk

    if not body:
        return b""

    payload = json.loads(
        body.decode(
            "utf-8"
        )
    )

    persist_screening_payload(
        payload
    )

    return body


async def database_persistence_dispatch(
    request: Request,
    call_next,
):

    response = await call_next(
        request
    )

    if (
        request.url.path
        not in TARGET_PATHS
    ):

        return response

    if response.status_code >= 400:

        return response

    try:

        body = await _persist_response(
            response
        )

        return Response(
            content=body,
            status_code=response.status_code,
            headers={
                key: value
                for key, value
                in response.headers.items()
                if key.lower()
                not in {
                    "content-length",
                    "content-type",
                }
            },
            media_type="application/json",
        )

    except Exception:

        # Screening must continue to work even if
        # database persistence has a temporary issue.

        return response
