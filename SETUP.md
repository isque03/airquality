# Developer setup

This guide is for contributors working on the Air Quality Dashboard.

## Requirements

- Python 3.10 or newer
- Internet access for provider requests and live smoke tests
- API keys only for the providers you want to enable

## Environment setup

The reproducible setup path is:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
cp .env.example .env
```

The included `setup.sh` performs the virtual-environment and application dependency installation:

```bash
./setup.sh
source .venv/bin/activate
```

Edit `.env` with your location and any provider credentials. `.env.example` is safe to commit; `.env` is not.

## API keys

Open-Meteo does not require a key for this application. The other integrations are optional:

- [AirNow API key](https://docs.airnowapi.org/account/request/)
- [OpenAQ account/API key](https://docs.openaq.org/using-the-api/api-key)
- [PurpleAir API key](https://develop.purpleair.com/keys)
- [IQAir AirVisual API key](https://www.iqair.com/air-quality-monitors/airvisual-platform/api)

Provider failures are isolated. A missing or invalid optional key should leave the other providers available and appear in the dashboard health panel.

## Configuration

The most useful settings are:

| Variable | Default | Purpose |
| --- | --- | --- |
| `LATITUDE` / `LONGITUDE` | `42.296` / `-71.292` | Search and forecast location |
| `ZIP_CODE` | `02481` | AirNow ZIP code |
| `SEARCH_RADIUS_KM` | `25` | Provider search radius |
| `POLL_INTERVAL_SECONDS` | `300` | Watch-mode polling interval |
| `REQUEST_TIMEOUT_SECONDS` | `20` | HTTP request timeout |
| `PROVIDER_TIMEOUT_SECONDS` | `10` | Per-provider collection timeout |
| `MAX_RETRIES` | `3` | Retry attempts for transient requests |
| `DATABASE_PATH` | `.data/airquality.db` | SQLite database path |
| `HISTORY_HOURS` | `24` | Chart window; does not delete stored history |
| `DEFAULT_METRIC` | `pm25` | Initial chart metric |
| `PLOT_WIDTH` / `PLOT_HEIGHT` | `72` / `20` | Chart dimensions |
| `COLOR_THEME` | `auto` | `auto`, `dark`, or `light` terminal palette |
| `PM25_ALERT_THRESHOLD` | empty | Optional PM2.5 alert threshold |
| `ENABLED_PROVIDERS` | all providers | Comma-separated provider names |

Supported metrics are `aqi_us`, `aqi_european`, `aqi_china`, `pm25`, `pm10`, `ozone`, `no2`, `co`, and `so2`.

## Running locally

```bash
python main.py --once
python main.py --once --metric pm25
python main.py --watch
NO_COLOR=1 python main.py --watch
```

The first run creates the SQLite database and stores observations with timestamps. Subsequent runs append new observations; history is retained indefinitely unless the configured database is deliberately removed.

## Tests and quality checks

Run the standard checks before submitting changes:

```bash
pytest -q
python -m compileall -q .
python -m pylint providers aqi.py config.py models.py storage.py history.py dashboard.py main.py \
  --disable=all --enable=wrong-import-order,ungrouped-imports,wrong-import-position,unused-import
python -m isort --check-only providers aqi.py config.py models.py storage.py history.py dashboard.py main.py tests
```

Tests use mocked provider payloads and do not require API keys. Live smoke testing requires a configured `.env`:

```bash
NO_COLOR=1 python main.py --once --metric pm25
```

### tmux and light terminals

No application-specific tmux integration is required. tmux forwards the terminal control sequences used by Rich and Plotext. If the layout or colors look wrong, check that the session has a real terminal type:

```bash
echo "$TERM"
tmux set-option -g default-terminal tmux-256color
```

The dashboard uses darker ANSI colors for light backgrounds and a taller default chart. `NO_COLOR=1` remains available when a terminal theme or multiplexer should receive plain text instead.

If auto-detection does not match the terminal, set the palette explicitly:

```bash
COLOR_THEME=light python main.py --watch
COLOR_THEME=dark python main.py --watch
```

## Contribution conventions

- Keep provider-specific parsing inside `providers/`.
- Normalize external payloads into `Observation` and `AQIReading` rather than leaking API shapes into the dashboard.
- Preserve AQI scale and provenance metadata; do not combine incompatible AQI scales.
- Keep database migrations backward-compatible for existing local SQLite files.
- Add unit tests for new parsing, calculations, failure paths, and persistence behavior.
- Do not commit `.env`, `.data/`, SQLite files, virtual environments, or API responses.
