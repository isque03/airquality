# Air Quality Dashboard

An async terminal dashboard that collects local air-quality observations from multiple providers, stores them in SQLite, and renders current conditions plus historical trends.

![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)
![SQLite](https://img.shields.io/badge/storage-SQLite-003B57?logo=sqlite&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)

## Highlights

- Open-Meteo modeled pollutants and European/U.S. AQI values without an API key.
- AirNow observations and U.S. AQI when an AirNow key is configured.
- OpenAQ v3, PurpleAir, and IQAir integrations when their keys are configured.
- Async provider polling with timeouts, retries, exponential backoff, and isolated provider failures.
- Indefinite SQLite history; the chart window is configurable and does not delete older observations.
- Rich full-screen watch dashboard with Plotext charts and keyboard metric navigation.
- Plain-text output fallback for CI, pipes, logs, and terminals without color support.
- PM2.5, PM10, ozone, NO₂, CO, SO₂, U.S. AQI, European AQI, and China AQI metrics.
- Threshold alerts and summary statistics.

## Quick start

```bash
git clone https://github.com/isque03/airquality.git
cd airquality

python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\\Scripts\\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

cp .env.example .env
python main.py --once
```

For the full developer workflow, including API keys, configuration, tests, and troubleshooting, see [SETUP.md](SETUP.md).

## Usage

Poll once and exit:

```bash
python main.py --once
python main.py --once --metric aqi_us
```

Run the live dashboard:

```bash
python main.py --watch
```

In watch mode, use `j`/`k` or the arrow keys to change the chart metric. Press `r` to refresh immediately and `q` to quit. Set `NO_COLOR=1` to use the plain-text polling view. `COLOR_THEME=auto` detects common terminal background hints; use `COLOR_THEME=light` or `COLOR_THEME=dark` to override it. Charts default to a 20-row height so their scales remain readable in tmux and light terminal themes.

## AQI interpretation

AQI scales are intentionally kept separate. The dashboard does not average or rank U.S., European, and China AQI values together.

- `aqi_us`: U.S. EPA scale. Provider-reported values are shown when available.
- `aqi_european`: European AQI values, currently supplied by Open-Meteo.
- `aqi_china`: China AQI values, currently supplied by IQAir.
- PurpleAir shows PM2.5 plus a clearly labeled `US calc` value calculated from the EPA PM2.5 breakpoints. Because the live PurpleAir value is a short-term sensor reading rather than an official 24-hour/nowcast AQI input, it is not presented as provider-reported AQI.

## Architecture

The application uses a small layered design:

```text
providers/       External API gateways and provider-specific normalization
polling.py       Async service layer for concurrent collection and failures
models.py        Observation, measurement, and AQI domain models
storage.py       SQLite observation repository
history.py      Metric series and fallback ASCII charting
dashboard.py    Rich/Plotext presentation and plain-text rendering
main.py         CLI composition and watch-mode lifecycle
```

Every provider is optional except Open-Meteo. Missing keys skip that provider without preventing the rest of the dashboard from running.

## Data and privacy

The default database is `.data/airquality.db`. It is local SQLite storage and is ignored by Git. API keys belong in `.env`, which is also ignored; never commit credentials or collected data.

## License

MIT. See [LICENSE](LICENSE).
