# Wear index ETL pipeline

Production style hourly ETL pipeline that ingests weather data from Open-Meteo, transforms it in PostgreSQL, and serves a feels-like temperature for Belgrade. 
Designed with idempotent loads, incremental ingestion, orchestrated with Airflow and containerized with Docker.

# Problem

Raw hourly temperature alone doesn't capture how cold it actually feels. 
This pipeline smooths temperature with window functions and combines it with wind speed to compute a feels-like index so you know what to wear.

# Architecture
- Open-Meteo API
- Python ETL
- Staging table
- UPSERT into weather_hourly
- Materialized view wear_now
- Airflow DAG

# Tech Stack
- Python (requests, pandas, SQLAlchemy, logging)
- PostgreSQL
- Apache Airflow (BashOperator, hourly schedule)
- Docker + Docker Compose
- Materialized Views + Window Functions

# Run Locally

## Prerequisites
- Docker
- Docker Compose
- `make` (Linux/Mac built-in)

> **Windows users:** use `./start.sh <command>` instead of `make <command>`.

## Setup

Clone the repository:
```bash
git clone https://github.com/LukaPokrajac/wear-index-pipeline.git
cd wear-index-pipeline
```

Start everything with a single command:
```bash
make up
```

This will:
1. Create the shared Docker network if it doesn't exist
2. Start the ETL stack (Python ETL + PostgreSQL)
3. Start the Airflow stack
4. Create the database tables
5. Create the `wear_now` materialized view

## Airflow UI

Open [http://localhost:8080](http://localhost:8080) — trigger the DAG manually or wait for the hourly schedule.  
Default credentials: `airflow / airflow`

## Query the wear index

Once the DAG has run at least once:
```bash
make query
```

Expected output:
```
       anchor_ts        | feels_like_c | label
------------------------+--------------+-------
 2026-02-12 01:00:00+00 |          5.1 | Cold
(1 row)
```

The view refreshes automatically after every DAG run.

## Tear down

```bash
make down
```

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