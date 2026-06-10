from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app as app_module


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("MERAKI_API_KEY", raising=False)
    app_module.app.config.update(TESTING=True, SECRET_KEY="test-secret")
    with app_module.app.test_client() as test_client:
        yield test_client


def flashed_messages(client):
    with client.session_transaction() as session:
        return list(session.get("_flashes", []))


def test_to_float_handles_valid_and_invalid_values():
    assert app_module._to_float("12.5") == 12.5
    assert app_module._to_float(None) is None
    assert app_module._to_float("abc") is None


def test_lat_lng_to_relative_position_projects_and_clamps():
    floor_plan = {
        "width": 200,
        "height": 100,
        "topLeftCorner": {"lat": 10.0, "lng": 20.0},
        "topRightCorner": {"lat": 10.0, "lng": 30.0},
        "bottomLeftCorner": {"lat": 0.0, "lng": 20.0},
    }

    relative = app_module.lat_lng_to_relative_position(5.0, 25.0, floor_plan)

    assert relative == {
        "x_ratio": pytest.approx(0.5),
        "y_ratio": pytest.approx(0.5),
        "x": pytest.approx(100.0),
        "y": pytest.approx(50.0),
    }

    clamped = app_module.lat_lng_to_relative_position(-5.0, 50.0, floor_plan)
    assert clamped["x_ratio"] == 1.0
    assert clamped["y_ratio"] == 1.0


def test_get_api_key_prefers_environment_value(monkeypatch):
    monkeypatch.setenv("MERAKI_API_KEY", "env-key")

    with app_module.app.test_request_context("/"):
        app_module.session["meraki_api_key"] = "session-key"
        assert app_module.get_api_key() == "env-key"


def test_fetch_floors_collects_floor_plans_and_network_metadata(monkeypatch):
    class FakeNetworks:
        def getNetworkFloorPlans(self, network_id):
            if network_id == "n2":
                raise app_module.meraki.APIError(
                    metadata={"tags": ["networks"], "operation": "getNetworkFloorPlans"},
                    response=SimpleNamespace(
                        status_code=404,
                        reason="Not Found",
                        text="missing",
                        json=lambda: {"errors": ["missing"]},
                    ),
                )
            return [{"floorId": f"{network_id}-floor"}]

    class FakeOrganizations:
        def getOrganizationNetworks(self, org_id):
            assert org_id == "org-1"
            return [
                {"id": "n1", "name": "HQ"},
                {"id": "n2", "name": "Branch"},
            ]

    fake_dashboard = SimpleNamespace(
        organizations=FakeOrganizations(),
        networks=FakeNetworks(),
    )
    monkeypatch.setattr(app_module, "get_dashboard", lambda api_key: fake_dashboard)

    floors = app_module.fetch_floors("api-key", "org-1")

    assert floors == [{"floorId": "n1-floor", "networkId": "n1", "networkName": "HQ"}]


def test_fetch_aps_filters_access_points_and_sorts_results(monkeypatch):
    class FakeNetworks:
        def getNetworkFloorPlan(self, network_id, floor_plan_id):
            assert network_id == "network-1"
            assert floor_plan_id == "floor-1"
            return {
                "devices": [{"mac": "aa:bb"}, {"mac": "cc:dd"}],
                "imageUrl": "https://example.test/floor.png",
                "width": 300,
                "height": 150,
                "topLeftCorner": {"lat": 10.0, "lng": 20.0},
                "topRightCorner": {"lat": 10.0, "lng": 30.0},
                "bottomLeftCorner": {"lat": 0.0, "lng": 20.0},
            }

        def getNetworkDevices(self, network_id):
            assert network_id == "network-1"
            return [
                {
                    "mac": "cc:dd",
                    "model": "MS120",
                    "name": "Switch",
                    "serial": "SERIAL-SW",
                    "lat": 5.0,
                    "lng": 25.0,
                },
                {
                    "mac": "aa:bb",
                    "model": "MR46",
                    "name": "Beta AP",
                    "serial": "SERIAL-AP",
                    "lat": 5.0,
                    "lng": 25.0,
                },
                {
                    "mac": "ee:ff",
                    "model": "MR36",
                    "name": "Other AP",
                    "serial": "SERIAL-OTHER",
                    "lat": 5.0,
                    "lng": 25.0,
                },
            ]

    class FakeWireless:
        def getDeviceWirelessStatus(self, serial):
            assert serial == "SERIAL-AP"
            return {
                "basicServiceSets": [
                    {"band": "5", "channel": 149, "power": 17},
                    {"band": "2.4", "channel": 6, "power": 9},
                ]
            }

    fake_dashboard = SimpleNamespace(
        networks=FakeNetworks(),
        wireless=FakeWireless(),
    )
    monkeypatch.setattr(app_module, "get_dashboard", lambda api_key: fake_dashboard)

    aps, floor_image = app_module.fetch_aps("api-key", "network-1", "floor-1")

    assert floor_image == {
        "url": "https://example.test/floor.png",
        "width": 300,
        "height": 150,
    }
    assert aps == [
        {
            "name": "Beta AP",
            "channel5": 149,
            "txPower5": 17,
            "channel24": 6,
            "txPower24": 9,
            "lat": 5.0,
            "lng": 25.0,
            "x": pytest.approx(150.0),
            "y": pytest.approx(75.0),
        }
    ]


def test_index_loads_organisations_when_api_key_present(client, monkeypatch):
    monkeypatch.setattr(
        app_module,
        "fetch_organisations",
        lambda api_key: [{"id": "org-1", "name": "Org One"}],
    )

    with client.session_transaction() as session:
        session["meraki_api_key"] = "session-key"

    response = client.get("/")

    assert response.status_code == 200
    assert b"Org One" in response.data


def test_set_api_key_stores_key_and_resets_selection_state(client):
    with client.session_transaction() as session:
        session["selected_org"] = {"id": "old"}
        session["floors"] = [{"id": "floor"}]
        session["selected_floor"] = {"id": "floor"}
        session["aps"] = [{"name": "AP 1"}]
        session["floor_image"] = {"url": "https://example.test/floor.png"}

    response = client.post("/api-key", data={"api_key": "new-key"})

    assert response.status_code == 302
    with client.session_transaction() as session:
        assert session["meraki_api_key"] == "new-key"
        assert "selected_org" not in session
        assert "floors" not in session
        assert "selected_floor" not in session
        assert "aps" not in session
        assert "floor_image" not in session
    assert flashed_messages(client) == [("success", "API key saved.")]


def test_select_org_fetches_floors_and_clears_previous_floor_state(client, monkeypatch):
    monkeypatch.setattr(
        app_module,
        "fetch_floors",
        lambda api_key, org_id: [{"floorId": "floor-1", "networkId": "network-1"}],
    )

    with client.session_transaction() as session:
        session["meraki_api_key"] = "session-key"
        session["selected_floor"] = {"id": "old-floor"}
        session["aps"] = [{"name": "Old AP"}]
        session["floor_image"] = {"url": "https://example.test/old.png"}

    response = client.post("/select-org", data={"org_id": "org-1", "org_name": "Org One"})

    assert response.status_code == 302
    with client.session_transaction() as session:
        assert session["selected_org"] == {"id": "org-1", "name": "Org One"}
        assert session["floors"] == [{"floorId": "floor-1", "networkId": "network-1"}]
        assert "selected_floor" not in session
        assert "aps" not in session
        assert "floor_image" not in session


def test_select_floor_fetches_aps_and_enables_auto_render(client, monkeypatch):
    monkeypatch.setattr(
        app_module,
        "fetch_aps",
        lambda api_key, network_id, floor_id: (
            [{"name": "AP 1", "x": 10, "y": 20}],
            {"url": "https://example.test/floor.png", "width": 200, "height": 100},
        ),
    )

    with client.session_transaction() as session:
        session["meraki_api_key"] = "session-key"

    response = client.post(
        "/select-floor",
        data={"floor_id": "floor-1", "floor_name": "Floor One", "network_id": "network-1"},
    )

    assert response.status_code == 302
    with client.session_transaction() as session:
        assert session["selected_floor"] == {
            "id": "floor-1",
            "name": "Floor One",
            "networkId": "network-1",
        }
        assert session["aps"] == [{"name": "AP 1", "x": 10, "y": 20}]
        assert session["floor_image"] == {
            "url": "https://example.test/floor.png",
            "width": 200,
            "height": 100,
        }
        assert session["auto_render_band"] == "5"


def test_fetch_aps_route_requires_selected_floor(client):
    response = client.post("/fetch-aps")

    assert response.status_code == 302
    assert flashed_messages(client) == [("warning", "Please select a floor plan first.")]


def test_floor_image_proxy_returns_meraki_image(client, monkeypatch):
    fake_response = SimpleNamespace(
        content=b"image-bytes",
        headers={"Content-Type": "image/jpeg"},
        raise_for_status=lambda: None,
    )
    monkeypatch.setattr(app_module.http_requests, "get", lambda url, timeout: fake_response)

    with client.session_transaction() as session:
        session["floor_image"] = {"url": "https://example.test/floor.jpg"}

    response = client.get("/floor-image")

    assert response.status_code == 200
    assert response.data == b"image-bytes"
    assert response.content_type == "image/jpeg"


def test_floor_image_proxy_returns_404_without_url(client):
    response = client.get("/floor-image")

    assert response.status_code == 404