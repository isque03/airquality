from abc import ABC, abstractmethod
from typing import Any

import httpx

from models import Observation


class Provider(ABC):
    name: str

    def __init__(self, client: httpx.AsyncClient):
        self.client = client

    @abstractmethod
    async def fetch(self) -> list[Observation]:
        ...

    async def close(self):
        return None


async def request_json(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    response = await client.request(method, url, params=params, headers=headers)
    response.raise_for_status()
    return response.json()
