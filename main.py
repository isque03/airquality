import argparse
import asyncio
import logging
import signal
import threading
from datetime import datetime, timezone

from alerts import AlertMonitor
from config import CONFIG
from dashboard import METRICS, DashboardRenderer, DashboardSnapshot
from http_client import RetryingHttpClient
from polling import PollingService, PollResult
from providers.airnow import AirNowProvider
from providers.iqair import IQAirProvider
from providers.openaq import OpenAQProvider
from providers.openmeteo import OpenMeteoProvider
from providers.purpleair import PurpleAirProvider
from storage import ObservationRepository

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def build_providers(client):
    available = {"openmeteo": OpenMeteoProvider, "airnow": AirNowProvider, "openaq": OpenAQProvider,
                 "purpleair": PurpleAirProvider, "iqair": IQAirProvider}
    return [available[name](client) for name in CONFIG.enabled_providers if name in available]


def parse_args():
    parser = argparse.ArgumentParser(description="Poll air-quality providers.")
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--once", action="store_true", help="poll once and exit")
    modes.add_argument("--watch", action="store_true", help="poll continuously")
    parser.add_argument("--metric", choices=METRICS, default=CONFIG.default_metric, help="initial chart metric")
    return parser.parse_args()


async def run(continuous: bool, initial_metric: str):
    client = RetryingHttpClient(CONFIG.request_timeout_seconds, CONFIG.max_retries, CONFIG.retry_base_seconds)
    repository = ObservationRepository(CONFIG.database_path)
    providers = build_providers(client)
    service = PollingService(providers, CONFIG.poll_interval_seconds, CONFIG.provider_timeout_seconds)
    alerts = AlertMonitor(CONFIG.alert_threshold, CONFIG.alert_cooldown_seconds)
    renderer = DashboardRenderer(CONFIG.plot_width, CONFIG.plot_height, CONFIG.color_theme)
    try:
        if continuous and CONFIG.color_enabled:
            await _run_interactive_watch(service, repository, alerts, renderer, initial_metric)
        elif continuous:
            await _run_plain_watch(service, repository, alerts, renderer, initial_metric)
        else:
            snapshot = await _collect(await service.poll_once(), repository, alerts, initial_metric)
            _print_snapshot(renderer, snapshot)
    finally:
        repository.close()
        await client.aclose()


async def _run_interactive_watch(service, repository, alerts, renderer, metric):
    from rich.live import Live

    controller = KeyboardController(metric)
    initial = DashboardSnapshot([], repository.since(CONFIG.history_hours), {}, metric, None, datetime.now(timezone.utc))
    loop = asyncio.get_running_loop()
    signals = _install_signal_handlers(loop, controller)
    state = {"snapshot": initial}
    with Live(renderer.render(initial), screen=True, auto_refresh=False, refresh_per_second=4) as live:
        keyboard_task = asyncio.create_task(controller.read_keys())
        resize_task = asyncio.create_task(_refresh_on_resize(live, renderer, state, controller))
        try:
            while not controller.quit:
                controller.wake.clear()
                snapshot = await _collect(await service.poll_once(), repository, alerts, controller.metric)
                state["snapshot"] = snapshot
                live.update(renderer.render(snapshot), refresh=True)
                try:
                    await asyncio.wait_for(controller.wake.wait(), CONFIG.poll_interval_seconds)
                except asyncio.TimeoutError:
                    pass
        finally:
            controller.stop()
            resize_task.cancel()
            await asyncio.gather(keyboard_task, resize_task, return_exceptions=True)
            _remove_signal_handlers(loop, signals)


async def _refresh_on_resize(live, renderer, state, controller):
    previous = renderer.dimensions()
    while not controller.quit:
        await asyncio.sleep(0.25)
        current = renderer.dimensions()
        if current != previous:
            previous = current
            live.update(renderer.render(state["snapshot"]), refresh=True)


def _install_signal_handlers(loop, controller):
    installed = []
    for event in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(event, controller.request_quit)
            installed.append(event)
        except (NotImplementedError, RuntimeError):
            continue
    return installed


def _remove_signal_handlers(loop, signals):
    for event in signals:
        loop.remove_signal_handler(event)


async def _run_plain_watch(service, repository, alerts, renderer, metric):
    while True:
        snapshot = await _collect(await service.poll_once(), repository, alerts, metric)
        _print_snapshot(renderer, snapshot)
        await asyncio.sleep(CONFIG.poll_interval_seconds)


async def _collect(result: PollResult, repository, alerts, metric: str) -> DashboardSnapshot:
    if result.observations:
        repository.save(result.observations)
    alert = alerts.evaluate(result.observations)
    return DashboardSnapshot(result.observations, repository.since(CONFIG.history_hours), result.errors,
                             metric, alert, datetime.now(timezone.utc))


def _print_snapshot(renderer, snapshot):
    print("Polling providers...", flush=True)
    if not CONFIG.color_enabled:
        print(renderer.render(snapshot, False))
        return
    try:
        from rich.console import Console
        Console(force_terminal=True, color_system="standard").print(renderer.render(snapshot, True))
    except ImportError:
        print(renderer.render(snapshot, False))
    if snapshot.alert:
        print(snapshot.alert)


class KeyboardController:
    def __init__(self, metric: str):
        self.metric_index = METRICS.index(metric)
        self.quit = False
        self.wake = asyncio.Event()
        self.shutdown = asyncio.Event()
        self.stop_event = threading.Event()

    @property
    def metric(self):
        return METRICS[self.metric_index]

    async def read_keys(self):
        try:
            import readchar
        except ImportError:
            return
        loop = asyncio.get_running_loop()

        def read_loop():
            while not self.stop_event.is_set():
                try:
                    key = readchar.readkey()
                except (KeyboardInterrupt, EOFError):
                    loop.call_soon_threadsafe(self.request_quit)
                    return
                loop.call_soon_threadsafe(self.handle_key, key)

        threading.Thread(target=read_loop, name="airquality-keyboard", daemon=True).start()
        await self.shutdown.wait()

    def request_quit(self):
        self.quit = True
        self.wake.set()
        self.shutdown.set()

    def stop(self):
        self.stop_event.set()
        self.request_quit()

    def handle_key(self, key: str):
        if key in ("q", "Q", "\x03"):
            self.quit = True
        elif key in ("j", "J", "\x1b[C"):
            self.metric_index = (self.metric_index + 1) % len(METRICS)
        elif key in ("k", "K", "\x1b[D"):
            self.metric_index = (self.metric_index - 1) % len(METRICS)
        elif key in ("r", "R"):
            pass
        else:
            return
        self.wake.set()


def main():
    args = parse_args()
    try:
        asyncio.run(run(args.watch, args.metric))
    except KeyboardInterrupt:
        return


if __name__ == "__main__":
    main()
