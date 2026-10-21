"""Llamadas reales a Open-Meteo (API gratuita, sin clave). Verifican que el servicio responde
con el formato que espera weather_tool. Excluir con: pytest -m "not integration"."""
import json

import openmeteo_requests
import pytest

from kids_planner.weather_tool import get_weekend_weather

from .conftest import call_tool

pytestmark = pytest.mark.integration

URL = "https://api.open-meteo.com/v1/forecast"
PARAMS = {
    "latitude": 40.5475,
    "longitude": -3.642,
    "hourly": ["temperature_2m", "precipitation_probability", "rain"],
    "forecast_days": 7,
}


def test_open_meteo_response_has_expected_shape():
    hourly = openmeteo_requests.Client().weather_api(URL, params=PARAMS)[0].Hourly()

    assert hourly.Interval() == 3600
    assert (hourly.TimeEnd() - hourly.Time()) // 3600 == 7 * 24
    for i in range(3):
        assert len(hourly.Variables(i).ValuesAsNumpy()) == 7 * 24


def test_get_weekend_weather_returns_sane_forecast():
    data = json.loads(call_tool(get_weekend_weather))
    rows = data["forecast"]

    assert rows, "la previsión no puede venir vacía"
    assert {r["weekday"] for r in rows} <= {"viernes", "sábado", "domingo"}
    assert {r["block"] for r in rows} <= {"mañana", "tarde"}
    for r in rows:
        assert -30 <= r["temp_min_c"] <= r["temp_max_c"] <= 50
        assert 0 <= r["rain_prob_max_pct"] <= 100
        assert r["rain_total_mm"] >= 0
