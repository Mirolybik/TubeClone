#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if ! command -v docker >/dev/null 2>&1; then
  echo "Ошибка: Docker не установлен. Установите Docker Desktop или Docker Engine." >&2
  exit 1
fi

if docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE=(docker-compose)
else
  echo "Ошибка: не найден docker compose (плагин) или docker-compose." >&2
  exit 1
fi

if [[ ! -f .env ]]; then
  cat > .env <<'EOF'
APP_PORT=8000
JWT_SECRET=change-me-in-production
MAX_UPLOAD_MB=1024
SEED_DEMO=true
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=admin
EOF
  echo "Создан .env с настройками по умолчанию."
fi

read_env() {
  local name="$1" fallback="$2"
  local value
  value="$(grep -E "^${name}=" .env | tail -n1 | cut -d= -f2- || true)"
  echo "${value:-$fallback}"
}

APP_PORT="$(read_env APP_PORT 8000)"
PROMETHEUS_PORT="$(read_env PROMETHEUS_PORT 9090)"
GRAFANA_PORT="$(read_env GRAFANA_PORT 3000)"
GRAFANA_ADMIN_USER="$(read_env GRAFANA_ADMIN_USER admin)"
GRAFANA_ADMIN_PASSWORD="$(read_env GRAFANA_ADMIN_PASSWORD admin)"

command="${1:-up}"

case "$command" in
  up)
    echo ""
    echo "  TubeClone запускается..."
    echo "  Приложение:  http://localhost:${APP_PORT}"
    echo "  Swagger:     http://localhost:${APP_PORT}/docs"
    echo "  Метрики:     http://localhost:${APP_PORT}/metrics"
    echo "  Prometheus:  http://localhost:${PROMETHEUS_PORT}"
    echo "  Grafana:     http://localhost:${GRAFANA_PORT}"
    echo "               ${GRAFANA_ADMIN_USER} / ${GRAFANA_ADMIN_PASSWORD}"
    echo ""
    echo "  Демо-аккаунты:"
    echo "    admin / Admin123!          (администратор)"
    echo "    moderator / Moder123!      (модератор)"
    echo "    creator / Creator123!      (автор)"
    echo "    user / User123!            (пользователь)"
    echo ""
    "${COMPOSE[@]}" up --build
    ;;
  down)
    "${COMPOSE[@]}" down
    ;;
  reset)
    echo "Останавливаю контейнеры и удаляю БД, медиафайлы и данные мониторинга..."
    "${COMPOSE[@]}" down -v
    ;;
  logs)
    "${COMPOSE[@]}" logs -f app
    ;;
  test)
    echo "Запускаю pytest в контейнере (SQLite, без демо-данных)..."
    "${COMPOSE[@]}" --profile test run --rm --build tests
    ;;
  *)
    echo "Использование: ./run.sh [up|down|reset|logs|test]"
    echo "  up     — собрать и запустить приложение, Prometheus и Grafana (по умолчанию)"
    echo "  down   — остановить контейнеры"
    echo "  reset  — остановить и удалить БД, медиафайлы и данные мониторинга"
    echo "  logs   — смотреть логи приложения"
    echo "  test   — запустить pytest в отдельном контейнере"
    exit 1
    ;;
esac
