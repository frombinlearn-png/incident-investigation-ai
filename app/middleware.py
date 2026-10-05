import asyncio
import logging
import time
from uuid import uuid4

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger("incident_ai")


def error_response(code: str, message: str, request_id: str, status: int) -> JSONResponse:
    return JSONResponse(
        {"error": {"code": code, "message": message, "request_id": request_id}},
        status_code=status,
    )


class RequestMiddleware:
    def __init__(self, app: ASGIApp, max_request_bytes: int) -> None:
        self.app = app
        self.max_request_bytes = max_request_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = uuid4().hex
        scope.setdefault("state", {})["request_id"] = request_id
        started = time.perf_counter()
        status_code = 500
        response_started = False

        async def tracked_send(message: Message) -> None:
            nonlocal status_code, response_started
            if message["type"] == "http.response.start":
                response_started = True
                status_code = message["status"]
                message["headers"] = [
                    *message.get("headers", []),
                    (b"x-request-id", request_id.encode("ascii")),
                ]
            await send(message)

        try:
            body = bytearray()
            try:
                async with asyncio.timeout(10):
                    while True:
                        message = await receive()
                        if message["type"] == "http.disconnect":
                            return
                        part = message.get("body", b"")
                        if len(body) + len(part) > self.max_request_bytes:
                            await error_response(
                                "request_too_large", "Request body is too large.", request_id, 413
                            )(scope, receive, tracked_send)
                            return
                        body.extend(part)
                        if not message.get("more_body", False):
                            break
            except TimeoutError:
                await error_response("request_timeout", "Request body timed out.", request_id, 408)(
                    scope,
                    receive,
                    tracked_send,
                )
                return
            delivered = False

            async def replay_receive() -> Message:
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {"type": "http.request", "body": bytes(body), "more_body": False}
                return await receive()

            await self.app(scope, replay_receive, tracked_send)
        except Exception:
            logger.error(
                "unexpected_error", extra={"request_id": request_id, "error_code": "internal_error"}
            )
            if response_started:
                raise
            await error_response(
                "internal_error", "An unexpected error occurred.", request_id, 500
            )(
                scope,
                receive,
                tracked_send,
            )
        finally:
            logger.info(
                "request_completed",
                extra={
                    "request_id": request_id,
                    "status_code": status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                },
            )
