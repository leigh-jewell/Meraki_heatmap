# 📡 Meraki RSSI Heatmap

> A Python Flask web app that generates a **predictive Wi-Fi RSSI heatmap** for Cisco Meraki floor plans — visualise signal coverage before you deploy.

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.1.0-green.svg)](https://github.com/leigh-jewell/Meraki_heatmap/releases)
[![Issues](https://img.shields.io/github/issues/leigh-jewell/Meraki_heatmap)](https://github.com/leigh-jewell/Meraki_heatmap/issues)

---

> This tool uses the Cisco Meraki Dashboard API to fetch AP locations and transmit power, then overlays a **predictive RSSI heatmap** on your floor plan image in the browser. Signal strength is estimated using the **Free Space Path Loss (FSPL)** model, rendered interactively with Plotly.

---

- ⚡ **Instant preview** — select a floor and the heatmap generates automatically
- 📶 **Dual-band support** — separate heatmaps for 2.4 GHz and 5 GHz
- 🗺️ **Floor plan overlay** — rendered directly on your Meraki floor plan image
- 🔒 **Secure** — uses the official Meraki Python SDK; no raw API calls
- 🌍 **Cross-platform** — runs anywhere Python 3.12+ is available
- 📦 **Minimal dependencies** — Flask, Meraki SDK, NumPy, Pandas, Matplotlib

---

## Quick Start

**1. Clone the repo:**

```bash
git clone https://github.com/leigh-jewell/Meraki_heatmap.git
cd Meraki_heatmap
```

**2. Install dependencies:**

Using [uv](https://docs.astral.sh/uv/) (recommended):
Flask app that builds a predictive Wi-Fi RSSI heatmap for Cisco Meraki floor plans.

## What It Does

- Uses the Meraki Dashboard API to load organisations, floor plans, and AP status.
- Converts AP geo coordinates to floor-plan-relative coordinates.
- Renders an interactive floor overlay + RSSI heatmap in the browser (Plotly).
- Supports per-band AP radio details for both 5 GHz and 2.4 GHz.

## Demo
![Demo](.github/images/demo.png)

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

Or with pip in a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install .
```

**3. Set your Meraki API key:**

```bash
export MERAKI_API_KEY=your_key_here
```

> You can also enter your API key directly in the navbar when the app opens — no environment variable required.

**4. Run the app:**

```bash
uv run flask run
```

Open the app at `http://127.0.0.1:5000`.

---

## How It Works

1. Select your **organisation** and **floor plan** from the navbar dropdowns.
2. AP data (location, channel, transmit power) is fetched automatically via the Meraki API.
3. Click **2.4 GHz** or **5 GHz** to generate the heatmap for that band.
4. Adjust the **RSSI cutoff slider** to filter signal strength thresholds.

Signal attenuation is calculated using **Free Space Path Loss**:

```
FSPL (dB) = 20·log10(d) + 20·log10(f) + 20·log10(4π/c)
```

---

## UI Overview

| Area | Description |
|---|---|
| **Navbar** | API key controls, organisation selector, floor selector |
| **AP Table** | Lists each AP with Name, 5 GHz Ch/Tx, 2.4 GHz Ch/Tx |
| **Heatmap Controls** | Band selector buttons and RSSI cutoff slider |
| **Floor Plan View** | Interactive Plotly overlay on the floor plan image |

---

## API Key Behaviour

| Method | Behaviour |
|---|---|
| `MERAKI_API_KEY` env var | Takes precedence on startup |
| Navbar input | Accepted per-session if env var is not set |

---

## Requirements

- Python 3.12+
- A Cisco Meraki Dashboard API key with access to organisations, networks, and floor plans

---

## Contributing

Contributions are welcome and greatly appreciated.

1. Fork the project
2. Create your feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

---

## License

This project is licensed under the [MIT License](LICENSE). It is provided as-is with no warranty — test in a non-production environment before use.

---

Made with ❤️ by [Leigh J](https://github.com/leigh-jewell)
