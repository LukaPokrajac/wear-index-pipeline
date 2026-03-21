from airflow import DAG
from airflow.providers.standard.operators.bash import BashOperator
from datetime import datetime, timedelta

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
        task_id = 'run_weather_pipeline',
        bash_command="python /opt/etl/src/load_pipeline.py",
        env={"DB_URL": "postgresql+psycopg2://etl:etl@etl_db_1:5432/weather"},
    )

    refresh_wear_now = BashOperator(
        task_id='refresh_wear_now',
        bash_command='psql postgresql://etl:etl@etl_db_1:5432/weather -c "REFRESH MATERIALIZED VIEW wear_now;"',
    )
 
    run_pipeline >> refresh_wear_now