# Copilot Instructions

## Project Overview

A Python Flask web app that generates a **predictive Wi-Fi RSSI heatmap** based on Cisco Meraki AP locations and transmit power. The heatmap is rendered as an overlay on a floor plan map in the browser.

**Core pipeline:**
1. AP data (location, transmit power, channel) is fetched via the **Meraki Python SDK**
2. Signal strength at each point is estimated using the **Free Space Path Loss (FSPL)** formula
3. Results are visualised using a **KDE (Kernel Density Estimation) classifier**
4. The heatmap overlay is rendered on an **HTML5 canvas** in the browser via JavaScript

## Running the App

```bash
uv run flask run
```

Set the Meraki API key via environment variable (or it can be entered through the frontend):

```bash
export MERAKI_API_KEY=your_key_here
```

## Architecture

```
app.py              # Flask app — all routes live here
<meraki_module>     # Meraki SDK wrapper (fetches orgs, networks, APs)
<heatmap_module>    # FSPL calculation + KDE heatmap generation
templates/          # Jinja2 HTML templates
static/             # JavaScript and CSS for the frontend
```

> Module names above are placeholders — update once files are added.

## Key Conventions

- **Single-file routing**: All Flask routes are in `app.py`. Do not introduce blueprints without discussion.
- **Meraki SDK**: Use `meraki` (the official Cisco Meraki Python SDK) for all API calls — do not use raw `requests` against the Meraki API.
- **Heatmap calculation**: Signal attenuation uses Free Space Path Loss: `FSPL(dB) = 20·log10(d) + 20·log10(f) + 20·log10(4π/c)`. Keep physics logic in the heatmap module, not in `app.py`.
- **KDE rendering**: The heatmap is generated server-side and passed to the frontend as data (not an image) for canvas rendering.
- **Jinja2 templates**: Frontend is server-rendered HTML with JavaScript — no separate frontend build step or bundler.
- **CSS framework**: Use **Bootstrap 3.4** for all UI styling. Do not introduce Bootstrap 4 or 5 or other CSS frameworks.
- **API key handling**: `MERAKI_API_KEY` env var takes precedence; if absent, the key is accepted from the frontend form and passed per-request.
