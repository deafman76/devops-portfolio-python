"""
FastAPI приложение для Фазы 1.

Этот сервис делает две вещи:
1. Обслуживает три эндпоинта: /, /healthz, /readyz.
2. Логирует всё в JSON-формате, как положено 12-factor приложению.

Конфиг читается из переменных окружения (OS env vars).
"""

import logging
import json
import os
from fastapi import FastAPI, HTTPException

# ============================================================================
# КОНФИГУРАЦИЯ (из переменных окружения)
# ============================================================================

APP_NAME = os.getenv("APP_NAME", "devops-portfolio-app")
APP_VERSION = os.getenv("APP_VERSION", "0.1.0")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# ============================================================================
# ЛОГИРОВАНИЕ (структурированное, в JSON)
# ============================================================================

# Настроим логирование так, чтобы каждая строка была валидный JSON.
# Это нужно для парсинга логов в Kubernetes и в ELK-стеке на Фазе 4.

class JSONFormatter(logging.Formatter):
    """Форматирует логи в JSON."""
    def format(self, record):
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        return json.dumps(log_data, ensure_ascii=False)


# Создаём логгер
logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)

# Обработчик в stdout (консоль)
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)

# ============================================================================
# ПРИЛОЖЕНИЕ (FastAPI)
# ============================================================================

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
)

# Глобальное состояние (для /readyz)
# Используется для имитации "приложение готово к работе"
app_is_ready = True


# ============================================================================
# ЭНДПОИНТЫ
# ============================================================================

@app.get("/")
def root():
    """
    Корневой эндпоинт. Возвращает информацию о приложении.
    
    Это содержательный эндпоинт, который что-то делает.
    На Фазе 2 здесь будет логика работы с DynamoDB.
    """
    logger.info("GET / called")
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "message": "Phase 1: Docker + CI/CD (hot reload works!)",
        "status": "ok",
    }


@app.get("/healthz")
def health():
    """
    Liveness probe для Kubernetes.
    
    Возвращает 200, если приложение живо (даже если не готово к работе).
    На Фазе 3 это будет использовано kubelet'ом для перезагрузки подов.
    """
    logger.debug("GET /healthz called")
    return {"status": "alive"}


@app.get("/readyz")
def ready():
    """
    Readiness probe для Kubernetes.
    
    Возвращает 200, только если приложение готово к работе.
    На Фазе 3 это будет использовано для маршрутизации трафика.
    """
    if not app_is_ready:
        logger.warning("GET /readyz called but app not ready")
        raise HTTPException(status_code=503, detail="Service not ready")
    
    logger.debug("GET /readyz called")
    return {"status": "ready"}


@app.post("/set-ready/{state}")
def set_ready_state(state: bool):
    """
    Утилита для тестирования readiness probe.
    
    Позволяет искусственно переключить состояние приложения.
    
    Используется в тестах: 
    - POST /set-ready/false → приложение "сломалось"
    - POST /set-ready/true → приложение "восстановилось"
    """
    global app_is_ready
    app_is_ready = state
    logger.info(f"App readiness state set to {state}")
    return {"ready": app_is_ready}


# ============================================================================
# MIDDLEWARE: логирование запросов
# ============================================================================

@app.middleware("http")
async def log_requests(request, call_next):
    """
    Логирует каждый HTTP-запрос в JSON-формате.
    """
    method = request.method
    path = request.url.path
    
    logger.info(f"Request started: {method} {path}")
    
    response = await call_next(request)
    
    logger.info(f"Request completed: {method} {path} {response.status_code}")
    
    return response


# ============================================================================
# ТОЧКА ВХОДА (для локального запуска)
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    # Локальный запуск с hot-reload
    # Используется для разработки, не для production
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # автоперезагрузка при изменении файлов
    )