import os
import logging
import requests as http_requests
import meraki
from flask import Flask, render_template, request, session, redirect, url_for, flash, Response

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(24))


def _to_float(value):
    """Safely convert a value to float; return None if conversion fails."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def lat_lng_to_relative_position(lat, lng, floor_plan):
    """Convert geographic coordinates to relative/pixel floor-image coordinates.

    Supports floor plans that provide geographic corners.
    Returns None if conversion cannot be performed.
    """
    width = _to_float(floor_plan.get("width"))
    height = _to_float(floor_plan.get("height"))
    if not width or not height:
        return None

    top_left = floor_plan.get("topLeftCorner", {})
    top_right = floor_plan.get("topRightCorner", {})
    bottom_left = floor_plan.get("bottomLeftCorner", {})

    tl_lat = _to_float(top_left.get("lat"))
    tl_lng = _to_float(top_left.get("lng"))
    tr_lat = _to_float(top_right.get("lat"))
    tr_lng = _to_float(top_right.get("lng"))
    bl_lat = _to_float(bottom_left.get("lat"))
    bl_lng = _to_float(bottom_left.get("lng"))

    lat = _to_float(lat)
    lng = _to_float(lng)
    if None in (lat, lng, tl_lat, tl_lng, tr_lat, tr_lng, bl_lat, bl_lng):
        return None

    # Solve the affine basis made by top-left -> top-right (x axis)
    # and top-left -> bottom-left (y axis): p = tl + u*x_axis + v*y_axis
    x_axis_lat = tr_lat - tl_lat
    x_axis_lng = tr_lng - tl_lng
    y_axis_lat = bl_lat - tl_lat
    y_axis_lng = bl_lng - tl_lng

    det = (x_axis_lng * y_axis_lat) - (x_axis_lat * y_axis_lng)
    if abs(det) < 1e-12:
        return None

    d_lat = lat - tl_lat
    d_lng = lng - tl_lng

    u = ((d_lng * y_axis_lat) - (d_lat * y_axis_lng)) / det
    v = ((x_axis_lng * d_lat) - (x_axis_lat * d_lng)) / det

    # Clamp so slightly off-floor devices still render on image edge.
    u = min(max(u, 0.0), 1.0)
    v = min(max(v, 0.0), 1.0)

    return {
        "x_ratio": u,
        "y_ratio": v,
        "x": u * width,
        "y": v * height,
    }

def get_api_key():
    """Return the Meraki API key from env var or session."""
    return os.environ.get("MERAKI_API_KEY") or session.get("meraki_api_key")

def get_dashboard(api_key):
    return meraki.DashboardAPI(api_key, suppress_logging=True)

def fetch_organisations(api_key):
    """Fetch all organisations accessible with the given API key."""
    logger.info("Fetching organisations")
    orgs = get_dashboard(api_key).organizations.getOrganizations()
    logger.info("Found %d organisation(s)", len(orgs))
    return orgs

def fetch_floors(api_key, org_id):
    """Fetch all floor plans across all networks in an organisation."""
    logger.info("Fetching floor plans for org %s", org_id)
    dashboard = get_dashboard(api_key)
    networks = dashboard.organizations.getOrganizationNetworks(org_id)
    logger.info("Found %d network(s) in org %s", len(networks), org_id)
    floors = []
    for network in networks:
        try:
            plans = dashboard.networks.getNetworkFloorPlans(network["id"])
            for plan in plans:
                plan["networkId"] = network["id"]
                plan["networkName"] = network["name"]
                floors.append(plan)
        except meraki.APIError:
            pass  # Network may not support floor plans
    logger.info("Found %d floor plan(s) for org %s", len(floors), org_id)
    return floors

def fetch_aps(api_key, network_id, floor_plan_id):
    """Fetch APs on a floor plan with radio details and floor device overlay metadata."""
    logger.info("Fetching APs for floor plan %s in network %s", floor_plan_id, network_id)
    dashboard = get_dashboard(api_key)

    # Get devices placed on this floor plan
    floor_plan = dashboard.networks.getNetworkFloorPlan(network_id, floor_plan_id)
    floor_macs = {d["mac"] for d in floor_plan.get("devices", [])}
    logger.info("Floor plan %s has %d device(s)", floor_plan_id, len(floor_macs))

    floor_image = {
        "url": floor_plan.get("imageUrl"),
        "width": floor_plan.get("width"),
        "height": floor_plan.get("height"),
    }
    logger.info("Floor plan image: %dx%d and url: %s", floor_image["width"] or 0, floor_image["height"] or 0, floor_image["url"])

    # Get device details (name, serial, lat, lng) — APs only (MR and CW model families)
    network_devices = dashboard.networks.getNetworkDevices(network_id)

    if not floor_macs:
        return [], floor_image

    device_map = {
        d["mac"]: d for d in network_devices
        if d.get("mac") in floor_macs
        and d.get("model", "").upper().startswith(("MR", "CW"))
    }
    logger.info(
        "Filtered to %d AP(s) from %d device(s) on floor plan",
        len(device_map), len(floor_macs),
    )

    aps = []
    for mac, device in device_map.items():
        serial = device.get("serial", "")

        # Get wireless radio status (channel, tx power) per band.
        bss_5 = {}
        bss_24 = {}
        if serial:
            try:
                status = dashboard.wireless.getDeviceWirelessStatus(serial)
                bss_list = status.get("basicServiceSets", [])
                bss_5 = next((b for b in bss_list if "5" in str(b.get("band", ""))), {})
                bss_24 = next((b for b in bss_list if "2.4" in str(b.get("band", ""))), {})
            except meraki.APIError as e:
                logger.warning("Could not fetch wireless status for %s: %s", serial, e)

        lat = device.get("lat", "N/A")
        lng = device.get("lng", "N/A")
        relative = lat_lng_to_relative_position(lat, lng, floor_plan)

        aps.append({
            "name": device.get("name") or mac,
            "channel5": bss_5.get("channel", "N/A"),
            "txPower5": bss_5.get("power", "N/A"),
            "channel24": bss_24.get("channel", "N/A"),
            "txPower24": bss_24.get("power", "N/A"),
            "lat": lat,
            "lng": lng,
            "x": relative["x"],
            "y": relative["y"],
        })

    aps = sorted(aps, key=lambda a: a["name"])
    logger.info("Returning %d AP(s) for floor plan %s", len(aps), floor_plan_id)
    return aps, floor_image

@app.route("/")
def index():
    api_key = get_api_key()
    organisations = []
    floors = []
    if api_key:
        try:
            organisations = fetch_organisations(api_key)
        except meraki.APIError as e:
            logger.error("Meraki API error fetching organisations: %s", e)
            flash(f"Meraki API error: {e.message}", "danger")
        except Exception as e:
            logger.exception("Unexpected error fetching organisations")
            flash(f"Failed to fetch organisations: {e}", "danger")

        if session.get("selected_org"):
            floors = session.get("floors", [])

    return render_template(
        "index.html",
        api_key_set=bool(api_key),
        organisations=organisations,
        selected_org=session.get("selected_org"),
        floors=floors,
        selected_floor=session.get("selected_floor"),
        aps=session.get("aps", []),
        floor_image=session.get("floor_image"),
        auto_render_band=session.pop("auto_render_band", None),
    )

@app.route("/api-key", methods=["POST"])
def set_api_key():
    key = request.form.get("api_key", "").strip()
    if key and not key.startswith("•"):
        session["meraki_api_key"] = key
        session.pop("selected_org", None)
        session.pop("floors", None)
        session.pop("selected_floor", None)
        session.pop("aps", None)
        session.pop("floor_image", None)
        logger.info("API key saved for session")
        flash("API key saved.", "success")
    elif not key:
        logger.warning("Empty API key submitted")
        flash("Please enter a valid API key.", "danger")
    return redirect(url_for("index"))

@app.route("/api-key/clear")
def clear_api_key():
    session.pop("meraki_api_key", None)
    session.pop("selected_org", None)
    session.pop("floors", None)
    session.pop("selected_floor", None)
    session.pop("aps", None)
    session.pop("floor_image", None)
    logger.info("API key cleared from session")
    flash("API key cleared.", "info")
    return redirect(url_for("index"))

@app.route("/select-org", methods=["POST"])
def select_org():
    org_id = request.form.get("org_id")
    org_name = request.form.get("org_name")
    if org_id:
        logger.info("Organisation selected: %s (%s)", org_name, org_id)
        session["selected_org"] = {"id": org_id, "name": org_name}
        session.pop("selected_floor", None)
        session.pop("aps", None)
        session.pop("floor_image", None)
        api_key = get_api_key()
        try:
            floors = fetch_floors(api_key, org_id)
            session["floors"] = floors
        except meraki.APIError as e:
            logger.error("Meraki API error fetching floors for org %s: %s", org_id, e)
            flash(f"Could not fetch floor plans: {e.message}", "warning")
            session["floors"] = []
        except Exception as e:
            logger.exception("Unexpected error fetching floors for org %s", org_id)
            flash(f"Could not fetch floor plans: {e}", "warning")
            session["floors"] = []
    return redirect(url_for("index"))

@app.route("/select-floor", methods=["POST"])
def select_floor():
    floor_id = request.form.get("floor_id")
    floor_name = request.form.get("floor_name")
    network_id = request.form.get("network_id")
    if floor_id:
        logger.info("Floor plan selected: %s (%s) in network %s", floor_name, floor_id, network_id)
        session["selected_floor"] = {
            "id": floor_id,
            "name": floor_name,
            "networkId": network_id,
        }
        session.pop("aps", None)
        session.pop("floor_image", None)

        api_key = get_api_key()
        try:
            aps, floor_image = fetch_aps(api_key, network_id, floor_id)
            session["aps"] = aps
            session["floor_image"] = floor_image
            session["auto_render_band"] = "5"
            if not aps:
                logger.info("No APs found on floor plan %s", floor_id)
                flash("No APs found on this floor plan.", "info")
        except meraki.APIError as e:
            logger.error("Meraki API error fetching APs after floor selection: %s", e)
            flash(f"Could not fetch APs: {e.message}", "danger")
        except Exception as e:
            logger.exception("Unexpected error fetching APs after floor selection")
            flash(f"Could not fetch APs: {e}", "danger")
    return redirect(url_for("index"))

@app.route("/fetch-aps", methods=["POST"])
def fetch_aps_route():
    selected_floor = session.get("selected_floor")
    if not selected_floor:
        logger.warning("Fetch APs requested but no floor plan selected")
        flash("Please select a floor plan first.", "warning")
        return redirect(url_for("index"))
    api_key = get_api_key()
    try:
        aps, floor_image = fetch_aps(api_key, selected_floor["networkId"], selected_floor["id"])
        session["aps"] = aps
        session["floor_image"] = floor_image
        if not aps:
            logger.info("No APs found on floor plan %s", selected_floor["id"])
            flash("No APs found on this floor plan.", "info")
    except meraki.APIError as e:
        logger.error("Meraki API error fetching APs: %s", e)
        flash(f"Could not fetch APs: {e.message}", "danger")
    except Exception as e:
        logger.exception("Unexpected error fetching APs")
        flash(f"Could not fetch APs: {e}", "danger")
    return redirect(url_for("index"))

@app.route("/floor-image")
def floor_image_proxy():
    """Proxy the floor plan image from Meraki to avoid CORS/expiry issues."""
    image_url = session.get("floor_image", {}).get("url")
    if not image_url:
        return "", 404
    try:
        resp = http_requests.get(image_url, timeout=10)
        resp.raise_for_status()
        content_type = resp.headers.get("Content-Type", "image/png")
        logger.info("Proxying floor image from Meraki (%s bytes)", len(resp.content))
        return Response(resp.content, content_type=content_type)
    except Exception as e:
        logger.error("Failed to proxy floor image: %s", e)
        return "", 502