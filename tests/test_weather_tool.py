import json
from datetime import datetime, timezone
from unittest.mock import MagicMock

import numpy as np

from kids_planner import weather_tool
from kids_planner.weather_tool import get_weekend_weather

from .conftest import call_tool

# Miércoles 21/10/2026 00:00 en Madrid (CEST) = martes 20/10 22:00 UTC. 7 días de datos horarios.
START = int(datetime(2026, 10, 20, 22, tzinfo=timezone.utc).timestamp())
HOURS = 7 * 24


def fake_openmeteo(monkeypatch, rain=1.0, prob=40.0, temp=15.0):
    values = [np.full(HOURS, temp), np.full(HOURS, prob), np.full(HOURS, rain)]
    hourly = MagicMock()
    hourly.Time.return_value = START
    hourly.TimeEnd.return_value = START + HOURS * 3600
    hourly.Interval.return_value = 3600
    hourly.Variables.side_effect = lambda i: MagicMock(ValuesAsNumpy=lambda: values[i])
    response = MagicMock()
    response.Hourly.return_value = hourly
    client = MagicMock()
    client.weather_api.return_value = [response]
    monkeypatch.setattr(weather_tool.openmeteo_requests, "Client", lambda session: client)
    monkeypatch.setattr(weather_tool, "retry", lambda session, **k: session)
    return client


def forecast(monkeypatch, **kwargs):
    fake_openmeteo(monkeypatch, **kwargs)
    return json.loads(call_tool(get_weekend_weather))["forecast"]


def test_only_friday_afternoon_and_weekend_blocks(monkeypatch):
    rows = forecast(monkeypatch)

    assert [(r["weekday"], r["block"]) for r in rows] == [
        ("viernes", "tarde"),
        ("sábado", "mañana"), ("sábado", "tarde"),
        ("domingo", "mañana"), ("domingo", "tarde"),
    ]
    assert [r["day"] for r in rows][0] == "2026-10-23"


def test_block_aggregation(monkeypatch):
    rows = {(r["weekday"], r["block"]): r for r in forecast(monkeypatch, rain=1.0, prob=40.0, temp=15.0)}

    assert rows[("sábado", "mañana")]["rain_total_mm"] == 5.0   # 9-13h
    assert rows[("sábado", "tarde")]["rain_total_mm"] == 6.0    # 14-19h
    assert rows[("viernes", "tarde")]["rain_total_mm"] == 4.0   # 16-19h
    assert rows[("sábado", "mañana")]["rain_prob_max_pct"] == 40.0
    assert rows[("sábado", "mañana")]["temp_min_c"] == rows[("sábado", "mañana")]["temp_max_c"] == 15.0


def test_requests_expected_variables(monkeypatch):
    client = fake_openmeteo(monkeypatch)
    call_tool(get_weekend_weather)

    params = client.weather_api.call_args.kwargs["params"]
    assert params["hourly"] == ["temperature_2m", "precipitation_probability", "rain"]
