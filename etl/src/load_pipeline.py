from datetime import datetime, timezone
import pandas as pd
import requests
from sqlalchemy import create_engine, text
import logging
import math
import os

logging.basicConfig(
    filename="pipeline.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
DB_URL = os.getenv("DB_URL", "postgresql+psycopg2://etl:etl@localhost:5432/weather")
OPEN_METEO_URL = 'https://api.open-meteo.com/v1/forecast'
LAT, LON = 44.8176, 20.4633 # Belgrade-ish

def fetch_open_meteo(past_days: int, forecast_days: int) -> dict:
    params = {
        'latitude': LAT,
        'longitude': LON,
        'hourly':'temperature_2m,precipitation,windspeed_10m',
        'timezone':'UTC',
        'past_days': past_days,
        'forecast_days': forecast_days,
    }
    r = requests.get(OPEN_METEO_URL, params=params, timeout=30)
    r.raise_for_status()
    return r.json()

def build_hourly_df(payload: dict, fetched_at: datetime) -> pd.DataFrame:
    hourly = payload['hourly']
    
    df = pd.DataFrame({
        'ts': pd.to_datetime(hourly['time'], utc=True),
        'temperature_c': hourly['temperature_2m'],
        'precipitation_mm': hourly.get('precipitation'), #.get() because precipitaton is optional and etl doesnt have to fail loudly if it fails
        'windspeed_kmh': hourly['windspeed_10m'],
    })
    df['source_fetched_at'] = pd.to_datetime(fetched_at, utc=True)

    df=df.dropna(subset=['ts']).drop_duplicates(subset=['ts'])
    return df

def load_df_to_postgres(df: pd.DataFrame, engine) -> None:
    df = df[['ts', 'temperature_c', 'precipitation_mm', 'windspeed_kmh', 'source_fetched_at']]
    sql_path = os.path.join(os.path.dirname(__file__), '..', 'sql', 'upsert_from_staging.sql')
    with open(sql_path, 'r') as f:
        upsert_sql = f.read()
    
    # 1. Load new data into staging
    df.to_sql(
        'stg_weather_hourly',
        engine,
        if_exists='append',
        index=False,
        method='multi'
    )
    # 2. Upsert into final table + truncate staging
    with engine.begin() as conn:
        conn.execute(text(upsert_sql))

def get_max_ts(engine) -> pd.Timestamp | None:
    with engine.connect() as conn:
        val = conn.execute(text("select max(ts) from weather_hourly")).scalar()
    if val is None:
        return None
    return pd.Timestamp(val).tz_convert("UTC") if pd.Timestamp(val).tzinfo else pd.Timestamp(val, tz="UTC")

def main():
    try:   
        engine = create_engine(DB_URL)
        now = pd.Timestamp(datetime.now(timezone.utc)).floor("h")
        max_ts = get_max_ts(engine)
        if max_ts is None:
            past_days = 2
        else:
            overlap_hours = 3
            effective_start = max_ts - pd.Timedelta(hours=overlap_hours)
            hours_behind = max(pd.Timedelta(0), now - effective_start)
            days_behind = math.ceil(hours_behind / pd.Timedelta(days=1))
            past_days = max(1, min(days_behind, 7)) # clamp between 1 and 7
        forecast_days = 2
        fetched_at = datetime.now(timezone.utc)
        payload = fetch_open_meteo(past_days=past_days, forecast_days=forecast_days)
        df = build_hourly_df(payload, fetched_at)
        load_df_to_postgres(df, engine)
        logging.info(f"OK: staged + upserted {len(df)} rows")
        print(f"OK: staged + upserted {len(df)} rows")
    except Exception as e:
        logging.error(f"Pipeline failed: {e}")
        raise

if __name__ == "__main__":
    main()