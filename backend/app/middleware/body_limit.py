"""ASGI ingress bound, before multipart parsing/spooling. Also bound proxy ingress."""

from starlette.formparsers import MultiPartException
from starlette.responses import JSONResponse

MAX_REQUEST_BYTES = 11 * 1024 * 1024


class BodyLimitMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = dict(scope.get("headers", []))
        try:
            length = int(headers.get(b"content-length", b"0"))
        except ValueError:
            return await JSONResponse(
                {"detail": "Invalid content length"}, status_code=400
            )(scope, receive, send)
        if length < 0 or length > MAX_REQUEST_BYTES:
            return await JSONResponse(
                {"detail": "Request exceeds 11 MiB"}, status_code=413
            )(scope, receive, send)
        total = 0
        exceeded = False
        rejected = False

        async def limited_receive():
            nonlocal total, exceeded
            message = await receive()
            total += len(message.get("body", b""))
            if total > MAX_REQUEST_BYTES:
                exceeded = True
                # The multipart parser closes its spooled files on this exception.
                raise MultiPartException("Request exceeds 11 MiB")
            return message

        async def limited_send(message):
            nonlocal rejected
            if exceeded:
                if not rejected:
                    rejected = True
                    await JSONResponse(
                        {"detail": "Request exceeds 11 MiB"}, status_code=413
                    )(scope, receive, send)
                return
            await send(message)

        await self.app(scope, limited_receive, limited_send)
