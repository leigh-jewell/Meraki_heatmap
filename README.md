# Meraki RSSI Heatmap

Flask app that builds a predictive Wi-Fi RSSI heatmap for Cisco Meraki floor plans.

## What It Does

- Uses the Meraki Dashboard API to load organisations, floor plans, and AP status.
- Converts AP geo coordinates to floor-plan-relative coordinates.
- Renders an interactive floor overlay + RSSI heatmap in the browser (Plotly).
- Supports per-band AP radio details for both 5 GHz and 2.4 GHz.

## Current UI Layout

- Top navbar contains:
	- Meraki API key input/save/clear controls
	- Organisation selector
	- Floor selector
- Organisation and Floor selectors are always visible.
	- When data is unavailable, they show disabled placeholder options.
- Selecting a floor automatically fetches AP data and floor image.
	- There is no manual "Fetch APs" button in the main page content.
- Heatmap controls include:
	- `2.4Ghz` and `5Ghz` generate buttons
	- Inline RSSI cutoff slider next to the buttons

## Access Points Table

The Access Points table includes:

- `Name`
- `5Ghz Ch`
- `5Ghz Tx (dBm)`
- `2.4Ghz Ch`
- `2.4Ghz Tx (dBm)`

The table no longer displays latitude/longitude columns.

## Requirements

- Python 3.10+
- A Cisco Meraki Dashboard API key with access to organisations/networks/floor plans

## Install

If needed, create and activate a virtual environment, then install dependencies from `pyproject.toml`.

Example with `uv`:

```bash
uv sync
```

## Run

```bash
uv run flask run
```

Open the app at:

```text
http://127.0.0.1:5000
```

## API Key Behavior

- `MERAKI_API_KEY` environment variable takes precedence.
- If the env var is not set, you can enter the API key in the navbar.
- UI-entered key is stored in Flask session only.

Example env var setup:

```bash
export MERAKI_API_KEY=your_key_here
```

## Notes

- Floor plan images are proxied through `/floor-image` to avoid CORS/expiry issues.
- If older AP data is already in session, refresh by re-selecting the floor.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
