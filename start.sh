#!/bin/bash
set -e

NETWORK_NAME="networkName"

case "$1" in
  up)
    echo ">>> Creating shared Docker network (if not exists)..."
    docker network inspect "$NETWORK_NAME" >/dev/null 2>&1 || docker network create "$NETWORK_NAME"
    echo ">>> Starting ETL stack..."
    docker-compose -f etl/docker-compose.yml up -d
    echo ">>> Starting Airflow stack..."
    docker-compose -f airflow/docker-compose.yml up -d
    echo ">>> All services are up."
    ;;
  down)
    echo ">>> Stopping Airflow stack..."
    docker-compose -f airflow/docker-compose.yml down
    echo ">>> Stopping ETL stack..."
    docker-compose -f etl/docker-compose.yml down
    echo ">>> All services stopped."
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
    echo "Usage: ./start.sh [up|down|logs|restart]"
    exit 1
    ;;
esac