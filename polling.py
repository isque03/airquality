import asyncio
import logging
from dataclasses import dataclass

from models import Observation
from providers.base import Provider

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PollResult:
    observations: list[Observation]
    errors: dict[str, Exception]


class PollingService:
    def __init__(self, providers: list[Provider], interval_seconds: float, provider_timeout_seconds: float = 10):
        self.providers = providers
        self.interval_seconds = interval_seconds
        self.provider_timeout_seconds = provider_timeout_seconds

    async def poll_once(self) -> PollResult:
        results = await asyncio.gather(*(self._fetch(provider) for provider in self.providers), return_exceptions=True)
        observations, errors = [], {}
        for provider, result in zip(self.providers, results):
            if isinstance(result, Exception):
                errors[provider.name] = result
                logger.warning("%s failed: %s", provider.name, result)
            else:
                observations.extend(result)
        return PollResult(observations, errors)

    async def _fetch(self, provider: Provider):
        try:
            return await asyncio.wait_for(provider.fetch(), self.provider_timeout_seconds)
        except asyncio.TimeoutError as error:
            raise TimeoutError(f"timed out after {self.provider_timeout_seconds:.0f}s") from error

    async def run_forever(self, on_result):
        while True:
            await on_result(await self.poll_once())
            await asyncio.sleep(self.interval_seconds)
