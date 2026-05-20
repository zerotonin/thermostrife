"""Per-tier weather-archive adapters.

Each adapter exposes ``fetch_daily_tmax(lat, lon, when, ...) -> Resolution``.
The cascade order is set by ``thermostrife.lookup.resolve``.
"""
