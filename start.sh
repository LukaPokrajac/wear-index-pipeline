#!/bin/bash
set -e

NETWORK_NAME="networkName"
PG_CONTAINER="etl_db_1"
PG_USER="etl"
PG_DB="weather"

case "$1" in
  up)
    echo ">>> Creating shared Docker network (if not exists)..."
    docker network inspect "$NETWORK_NAME" >/dev/null 2>&1 || docker network create "$NETWORK_NAME"
    echo ">>> Starting ETL stack..."
    docker-compose -f etl/docker-compose.yml up -d
    echo ">>> Starting Airflow stack..."
    docker-compose -f airflow/docker-compose.yml up -d
    echo ">>> Waiting for Postgres to be ready..."
    until docker exec "$PG_CONTAINER" pg_isready -U "$PG_USER" >/dev/null 2>&1; do sleep 1; done
    echo ">>> Creating tables..."
    docker exec -i "$PG_CONTAINER" psql -U "$PG_USER" -d "$PG_DB" < etl/sql/schema.sql
    echo ">>> Creating wear_now materialized view..."
    docker exec -i "$PG_CONTAINER" psql -U "$PG_USER" -d "$PG_DB" < etl/sql/wear_now.sql
    echo ">>> All services are up."
    ;;
  down)
    echo ">>> Stopping Airflow stack..."
    docker-compose -f airflow/docker-compose.yml down
    echo ">>> Stopping ETL stack..."
    docker-compose -f etl/docker-compose.yml down
    echo ">>> All services stopped."
    ;;
  query)
    docker exec -i "$PG_CONTAINER" psql -U "$PG_USER" -d "$PG_DB" -c \
    "SELECT anchor_ts, feels_like_c, label FROM wear_now WHERE anchor_ts <= now() ORDER BY anchor_ts DESC LIMIT 1;"
    ;;
  logs)
    echo ">>> ETL logs:"
    docker-compose -f etl/docker-compose.yml logs --tail=50
    echo ">>> Airflow logs:"
    docker-compose -f airflow/docker-compose.yml logs --tail=50
    ;;
  restart)
    $0 down
    $0 up
    ;;
  *)
    echo "Usage: ./start.sh [up|down|query|logs|restart]"
    exit 1
    ;;
esac