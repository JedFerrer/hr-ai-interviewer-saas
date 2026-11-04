"""Owned backend entrypoint installs network denial before application import."""

import os

from app.demo.guard import require_demo
from app.demo.network import install

require_demo()
install()

if __name__ == "__main__":
    import hashlib
    import hmac

    import uvicorn
    from fastapi import Request
    from fastapi.responses import PlainTextResponse

    from app.main import app

    @app.get("/__portfolio-proof", include_in_schema=False)
    async def proof(request: Request):
        require_demo()
        nonce = request.headers.get("x-portfolio-nonce", "")
        return PlainTextResponse(
            hmac.new(
                os.environ["HR_OWNED_TOKEN"].encode(), nonce.encode(), hashlib.sha256
            ).hexdigest()
        )

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=int(os.environ["HR_API_PORT"]),
        workers=1,
        proxy_headers=False,
        access_log=False,
    )
