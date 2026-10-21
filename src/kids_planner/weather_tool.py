import json
import numpy as np
import openmeteo_requests
import pandas as pd
import requests

from agents import function_tool
from retry_requests import retry

@function_tool
def get_weekend_weather():
    """Devuelve la previsión meteorológica del próximo fin de semana (viernes, sábado y domingo)
    para Alcobendas, San Sebastián de los Reyes y el norte de Madrid, dividida en
    mañana (9-14h) y tarde (14-20h). Úsala para decidir entre planes de interior
    o exterior. No necesita parámetros."""

    TZ = "Europe/Madrid"
    WEEKDAYS_ES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": 40.5475,
        "longitude": -3.642,
        "hourly": ["temperature_2m", "precipitation_probability", "rain"],
        "forecast_days": 7,
    }

    retry_session = retry(requests.Session(), retries=3, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)
    response = openmeteo.weather_api(url, params=params)[0]
    hourly = response.Hourly()

    df = pd.DataFrame({
        "date": pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
            end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=hourly.Interval()),
            inclusive="left",
        ),
        "temperature_2m": hourly.Variables(0).ValuesAsNumpy(),
        "precipitation_probability": hourly.Variables(1).ValuesAsNumpy(),
        "rain": hourly.Variables(2).ValuesAsNumpy(),
    })
    
    df["date"] = df["date"].dt.tz_convert(TZ)

    mask = (
    ((df["date"].dt.weekday == 4) & df["date"].dt.hour.between(16, 19))
    | (df["date"].dt.weekday.isin([5, 6]) & df["date"].dt.hour.between(9, 19)))
    df = df[mask].copy()

    df["day"] = df["date"].dt.date
    df["block"] = df["date"].dt.hour.map(lambda h: "mañana" if h < 14 else "tarde")

    summary = (
        df.groupby(["day", "block"])
        .agg(
            temp_min_c=("temperature_2m", "min"),
            temp_max_c=("temperature_2m", "max"),
            rain_prob_max_pct=("precipitation_probability", "max"),
            rain_total_mm=("rain", "sum"),
        )
        .round(1)
        .reset_index()
    )
    summary["weekday"] = summary["day"].map(lambda d: WEEKDAYS_ES[d.weekday()])
    summary["day"] = summary["day"].astype(str)

    return json.dumps({
        "location": "Alcobendas / San Sebastián de los Reyes / norte de Madrid",
        "timezone": TZ,
        "units": {"temperature": "°C", "rain_prob": "%", "rain": "mm"},
        "forecast": summary.to_dict(orient="records"),
    }, ensure_ascii=False)