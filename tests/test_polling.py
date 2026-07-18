import asyncio
from datetime import datetime, timezone

from models import Observation
from polling import PollingService


class Provider:
    def __init__(self, name, result=None, error=None):
        self.name, self.result, self.error = name, result, error

    async def fetch(self):
        if self.error:
            raise self.error
        return self.result or []


def test_poll_once_isolates_provider_failures():
    good = Observation("good", "station", 1, 2, datetime.now(timezone.utc), pm25=4)
    service = PollingService([Provider("good", [good]), Provider("bad", error=ValueError("offline"))], 60)

    result = asyncio.run(service.poll_once())

    assert result.observations == [good]
    assert isinstance(result.errors["bad"], ValueError)


def test_poll_once_times_out_slow_provider():
    class SlowProvider(Provider):
        async def fetch(self):
            await asyncio.sleep(1)

    service = PollingService([SlowProvider("slow")], 60, provider_timeout_seconds=0.01)
    result = asyncio.run(service.poll_once())
    assert isinstance(result.errors["slow"], TimeoutError)
