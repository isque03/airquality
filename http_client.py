import asyncio
import logging
import random
from collections.abc import Awaitable, Callable

import httpx

logging.getLogger("httpx").setLevel(logging.WARNING)


class RetryingHttpClient:
    def __init__(self, timeout: float, retries: int, base_delay: float):
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(timeout))
        self._retries = retries
        self._base_delay = base_delay

    async def request(self, method, url, **kwargs):
        for attempt in range(self._retries + 1):
            try:
                response = await self._client.request(method, url, **kwargs)
                if response.status_code < 500 or attempt == self._retries:
                    return response
            except (httpx.TimeoutException, httpx.NetworkError):
                if attempt == self._retries:
                    raise
            await asyncio.sleep(self._base_delay * (2 ** attempt) + random.random() * 0.1)

    async def aclose(self):
        await self._client.aclose()
