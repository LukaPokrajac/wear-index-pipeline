# Wear index ETL pipeline

Production style hourly pipeline that ingests weather data from Open-Meteo, transforms it in PostgreSQL, and serves a feels-like temperature index for Belgrade. 
Fully orchestrated with Apache Airflow and containerized with Docker.

# Problem

Raw hourly temperature alone doesn't capture how cold it actually feels. 
This pipeline smooths temperature with window functions and combines it with wind speed to compute a feels-like index so you know what to wear.

# Architecture

Open-Meteo API
Python ETL
Staging table
UPSERT into weather_hourly
Materialized view wear_now
Airflow DAG

# Tech Stack

Python (requests, pandas, SQLAlchemy, logging)
PostgreSQL 
Apache Airflow (BashOperator, hourly schedule)
Docker + DockerCompose
Materialized Views + Window Functions

# Run locally

Start both environments (shared Docker network required):

docker-compose up -d  # ETL + Postgres
docker-compose up -d  # Airflow

Trigger DAG manually or wait for hourly schedule in Airflow UI at localhost:8080

Run wear_now.sql or wear_index.py

# Example output

select anchor_ts, feels_like_c, label
from wear_now
order by anchor_ts
limit 1;

       anchor_ts        | feels_like_c | label
------------------------+--------------+-------
 2026-02-12 01:00:00+00 |          5.1 | Cold
(1 row)

# Design Decisions

- UPSERT with ON CONFLICT makes loads idempotent — safe to re-run anytime
- 3-hour overlap in incremental loading avoids boundary gaps
- DISTINCT ON (ts) in staging query prevents duplicate conflict errors
- Window functions smooth temperature noise before computing feels-like
- Materialized view serves wear index at low latency instead of computing on request
- Separate staging table decouples ingestion from final table, following standard ETL pattern
- BashOperator used over PythonOperator to keep Airflow and ETL dependency environments isolated

# Future Improvements

- Deploy to AWS (EC2 + RDS)
- Add unit tests
- Add FastAPI endpoint for wear index
- Implement Airflow Connections for credential management