import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


logger = logging.getLogger("linkpulse.access")


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()

        response = await call_next(request)

        duration_ms = (time.perf_counter() - start_time) * 1000
        request_id = getattr(request.state, "request_id", "-")
        client_ip = request.client.host if request.client else "-"

        logger.info(
            f"{request.method} {request.url.path} "
            f"status={response.status_code} "
            f"duration={duration_ms:.2f}ms "
            f"ip={client_ip} "
            f"request_id={request_id}"
        )

        return response
