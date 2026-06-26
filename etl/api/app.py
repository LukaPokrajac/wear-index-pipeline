from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import create_engine, text

# Inside Docker the db service is reachable as host "db" on the shared network.
DB_URL = os.getenv("DB_URL", "postgresql+psycopg2://etl:etl@db:5432/weather")

# How many upcoming hours to show in the forecast strip.
FORECAST_HOURS = 12

engine = create_engine(DB_URL, pool_pre_ping=True)

app = FastAPI(title="Wear Index")

STATIC_DIR = Path(__file__).parent / "static"

CURRENT_SQL = text(
    """
    select anchor_ts, feels_like_c, label
    from wear_now
    where anchor_ts <= now()
    order by anchor_ts desc
    limit 1
    """
)

FORECAST_SQL = text(
    """
    select anchor_ts, feels_like_c, label
    from wear_now
    where anchor_ts > now()
    order by anchor_ts asc
    limit :limit
    """
)


def _row_to_dict(row) -> dict:
    return {
        "anchor_ts": row.anchor_ts.isoformat(),
        "feels_like_c": float(row.feels_like_c) if row.feels_like_c is not None else None,
        "label": row.label,
    }


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/wear")
def wear():
    try:
        with engine.connect() as conn:
            current_row = conn.execute(CURRENT_SQL).fetchone()
            forecast_rows = conn.execute(
                FORECAST_SQL, {"limit": FORECAST_HOURS}
            ).fetchall()
    except Exception as exc:  # db not ready / view missing
        return JSONResponse(
            status_code=503,
            content={"error": "data unavailable", "detail": str(exc)},
        )

    if current_row is None:
        return JSONResponse(
            status_code=404,
            content={"error": "no wear data yet — run the DAG at least once"},
        )

    return {
        "city": "Belgrade",
        "current": _row_to_dict(current_row),
        "forecast": [_row_to_dict(r) for r in forecast_rows],
    }
