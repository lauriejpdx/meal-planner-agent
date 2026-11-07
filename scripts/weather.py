#!/usr/bin/env python3
"""7-day forecast for a US ZIP code (Zippopotam for coordinates, Open-Meteo for weather; no API keys).

Usage: weather.py <zip>
Output: JSON with one entry per day: date, weekday, high/low (F), rain chance, and a feel label.
"""
import datetime as dt
import json
import sys
import urllib.request


def get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=20) as resp:
        return json.load(resp)


def feel(high: float, rain: int) -> str:
    if high < 50:
        return "cold"
    if high < 65:
        return "cool + rainy" if rain >= 50 else "cool"
    if high < 80:
        return "mild + rainy" if rain >= 50 else "mild"
    return "hot"


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    place = get_json(f"https://api.zippopotam.us/us/{sys.argv[1]}")["places"][0]
    lat, lon = place["latitude"], place["longitude"]
    daily = get_json(
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max"
        "&temperature_unit=fahrenheit&timezone=auto&forecast_days=7"
    )["daily"]

    days = []
    for date, hi, lo, rain in zip(daily["time"], daily["temperature_2m_max"],
                                  daily["temperature_2m_min"], daily["precipitation_probability_max"]):
        days.append({
            "date": date,
            "weekday": dt.date.fromisoformat(date).strftime("%a"),
            "high_f": round(hi),
            "low_f": round(lo),
            "rain_pct": rain,
            "feel": feel(hi, rain),
        })
    json.dump({"place": f'{place["place name"]}, {place["state abbreviation"]}', "days": days},
              sys.stdout, indent=2)


if __name__ == "__main__":
    main()
