# Wear index ETL pipeline

Production style hourly ETL pipeline that ingests weather data from Open-Meteo, transforms it in PostgreSQL, and serves a feels-like temperature for Belgrade.
Designed with idempotent loads, incremental ingestion, orchestrated with Airflow and containerized with Docker.

# Problem

Raw hourly temperature alone doesn't capture how cold it actually feels. 
This pipeline smooths temperature with window functions and combines it with wind speed to compute a feels-like index so you know what to wear.

# Architecture

## Pipeline Flow
Open-Meteo API → Python ETL → Staging table → UPSERT into weather_hourly → Materialized view wear_now → Airflow DAG (hourly)

## Infrastructure
- AWS EC2 — runs Docker Compose, Airflow, and ETL
- AWS RDS — PostgreSQL database

# Tech Stack
- Python (requests, pandas, SQLAlchemy, logging)
- PostgreSQL
- Apache Airflow (BashOperator, hourly schedule)
- Docker + Docker Compose
- Materialized Views + Window Functions
- AWS (EC2 + RDS)

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

### Public repo safety

- Secrets are **not** stored in code; database URL comes from environment variable `WEATHER_DB_URL`.
- Keep credentials in a local repo-root `.env` file (gitignored), never in tracked files.
- If a real password was ever exposed, rotate it before publishing.

### Optional: use AWS RDS locally

Create a repo-root `.env` file:
```bash
WEATHER_DB_URL=postgresql+psycopg2://USER:PASSWORD@your-instance.region.rds.amazonaws.com:5432/weather
```

Then start as usual:
```bash
make up
```

This will:
1. Create the shared Docker network if it doesn't exist
2. Start the ETL stack (Python ETL + PostgreSQL)
3. Start the Airflow stack
4. Create the database tables
5. Create the `wear_now` materialized view

### Deploy to AWS (EC2 + RDS)

This project can run the Airflow + ETL containers on an EC2 instance, while storing the weather tables on AWS RDS.

#### AWS prerequisites

1. An RDS PostgreSQL instance (port `5432`), with a database named `weather`.
2. An RDS user/password that matches your `WEATHER_DB_URL` (default examples use user `etl`).
3. Network/security configuration:
   - Allow EC2 to connect to RDS on `5432` (RDS inbound from the EC2 security group).

#### Configure the repo on EC2

On the EC2 host, create a repo-root `.env` file (it is gitignored):

```bash
WEATHER_DB_URL=postgresql+psycopg2://USER:PASSWORD@your-rds-endpoint:5432/weather
```

Then bring everything up:

```bash
make up
```

#### Initialize the RDS schema (one-time)

Because `make up` creates tables/materialized views in the local Postgres container, you must create them in RDS too (so the DAG can load + refresh there).

Create the tables:

```bash
WEATHER_PSQL_URL=$(echo "$WEATHER_DB_URL" | sed 's#^postgresql+psycopg2://#postgresql://#')
docker run --rm -i \
  --network networkName \
  postgres:16 \
  psql "$WEATHER_PSQL_URL" -f etl/sql/schema.sql
```

Create the `wear_now` materialized view:

```bash
docker run --rm -i \
  --network networkName \
  postgres:16 \
  psql "$WEATHER_PSQL_URL" -f etl/sql/wear_now.sql
```

After that, open the Airflow UI and trigger the `weather_etl` DAG once.

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

- Add unit tests
- Add FastAPI endpoint for wear index
- Implement Airflow Connections for credential management
