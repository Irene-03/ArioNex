"""
/// <summary>
/// میدل‌ور محدودکننده نرخ درخواست‌ها جهت مقابله با حملات منع سرویس (Rate Limiter Middleware for DoS Protection)
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
    /// میدل‌ور پیشگیری از سوءاستفاده از منابع سرور با پیاده‌سازی پنجره لغزان (Sliding Window Rate Limiter)
    /// </summary>
    """
    # نگهداری تاریخچه درخواست هر کلاینت بر اساس آی‌پی در حافظه موقت (In-Memory)
    request_history = defaultdict(list)

    def __init__(self, app, requests_limit: int = 30, window_seconds: int = 60):
        super().__init__(app)
        self.requests_limit = requests_limit
        self.window_seconds = window_seconds

    async def dispatch(self, request: Request, call_next):
        # اعمال محدودیت فقط روی اندپوینت‌های عمومی API (آدرس‌های شروع شونده با v1)
        if request.url.path.startswith("/v1/"):
            client_ip = request.client.host if request.client else "unknown"
            current_time = time.time()

            # پاکسازی رکوردهای منقضی‌شده خارج از پنجره زمانی
            history = self.request_history[client_ip]
            valid_history = [t for t in history if current_time - t < self.window_seconds]
            self.request_history[client_ip] = valid_history

            # بررسی تجاوز از سقف مجاز
            if len(valid_history) >= self.requests_limit:
                logger.warning(f"Rate limit exceeded for client {client_ip} on path {request.url.path}")
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "تعداد درخواست‌های شما بیش از حد مجاز است. لطفاً کمی صبر کرده و سپس مجدداً تلاش کنید."
                    },
                    headers={"Retry-After": str(self.window_seconds)}
                )

            # ثبت زمان درخواست جدید
            self.request_history[client_ip].append(current_time)

        return await call_next(request)
