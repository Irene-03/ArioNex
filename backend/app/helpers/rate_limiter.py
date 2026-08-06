"""
/// <summary>
/// Request rate-limiting middleware to counter denial-of-service attacks (Rate Limiter Middleware for DoS Protection)
/// </summary>
"""

import time
import logging
from collections import defaultdict
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("arionex.rate_limiter")

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    /// <summary>
    /// Middleware that prevents abuse of server resources using a sliding window (Sliding Window Rate Limiter)
    /// </summary>
    """
    # Keeps the request history of each client by IP in temporary memory (In-Memory)
    request_history = defaultdict(list)

    def __init__(self, app, requests_limit: int = 30, window_seconds: int = 60):
        super().__init__(app)
        self.requests_limit = requests_limit
        self.window_seconds = window_seconds

    async def dispatch(self, request: Request, call_next):
        # Apply the limit only to public API endpoints (paths starting with v1)
        if request.url.path.startswith("/v1/"):
            client_ip = request.client.host if request.client else "unknown"
            current_time = time.time()

            # Clean up expired records outside the time window
            history = self.request_history[client_ip]
            valid_history = [t for t in history if current_time - t < self.window_seconds]
            self.request_history[client_ip] = valid_history

            # Check whether the allowed limit is exceeded
            if len(valid_history) >= self.requests_limit:
                logger.warning(f"Rate limit exceeded for client {client_ip} on path {request.url.path}")
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "تعداد درخواست‌های شما بیش از حد مجاز است. لطفاً کمی صبر کرده و سپس مجدداً تلاش کنید."
                    },
                    headers={"Retry-After": str(self.window_seconds)}
                )

            # Record the time of the new request
            self.request_history[client_ip].append(current_time)

        return await call_next(request)
