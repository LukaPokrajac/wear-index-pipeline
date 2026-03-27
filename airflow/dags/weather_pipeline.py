import os
import re
from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.standard.operators.bash import BashOperator

# Set WEATHER_DB_URL in the environment (see airflow/docker-compose.yaml) or in a gitignored .env at repo root.
# Default matches local `make up`: ETL Postgres service `db` on the shared Docker network.
_DEFAULT_WEATHER_DB_URL = "postgresql+psycopg2://etl:etl@db:5432/weather"
WEATHER_DB_URL = os.environ.get("WEATHER_DB_URL", _DEFAULT_WEATHER_DB_URL)


def _sqlalchemy_url_to_psql(url: str) -> str:
    """psql expects postgresql://… not postgresql+psycopg2://…"""
    return re.sub(r"^postgresql\+[^:]+://", "postgresql://", url, count=1)


_PSQL_URL = _sqlalchemy_url_to_psql(WEATHER_DB_URL)

with DAG(
    dag_id='weather_etl',
    start_date=datetime(2026, 3, 15),
    schedule='@hourly',
    catchup=False,
    default_args={
        'retries': 0,
        'retry_delay': timedelta(minutes=5)},
) as dag:

    run_pipeline = BashOperator(
        task_id='run_weather_pipeline',
        bash_command="python /opt/etl/src/load_pipeline.py",
        env={"DB_URL": WEATHER_DB_URL},
    )

    refresh_wear_now = BashOperator(
        task_id='refresh_wear_now',
        bash_command='psql "$PSQL_URL" -c "REFRESH MATERIALIZED VIEW wear_now;"',
        env={"PSQL_URL": _PSQL_URL},
    )

    run_pipeline >> refresh_wear_now
