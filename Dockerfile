# ============================================================================
# ФАЗА 1: Builder (подготовка зависимостей)
# ============================================================================
# Цель: скачать все Python-пакеты и подготовить виртуальное окружение.
# Это нужно для того, чтобы финальный образ был маленьким.

FROM python:3.11-slim as builder

# Устанавливаем зависимости для сборки (нужны для некоторых пакетов)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Создаём виртуальное окружение
RUN python -m venv /opt/venv
# Активируем его для всех последующих команд
ENV PATH="/opt/venv/bin:$PATH"

# Копируем requirements.txt (и только его!)
# Это делается в отдельном слое, чтобы Docker кешировал зависимости.
# Если код меняется, но requirements.txt нет — Docker переиспользует старый слой.
COPY requirements.txt .

# Устанавливаем зависимости в виртуальное окружение
RUN pip install --no-cache-dir -r requirements.txt


# ============================================================================
# ФАЗА 2: Runtime (финальный образ)
# ============================================================================
# Цель: максимально лёгкий образ, содержащий только нужное для запуска.

FROM python:3.11-slim

# Метаданные образа (опционально, но хорошая практика)
LABEL maintainer="devops-portfolio"
LABEL description="Phase 1: Docker + CI/CD - FastAPI application"

# Копируем виртуальное окружение из builder'а
# Это трюк: всё уже скомпилировано, просто копируем готовое.
COPY --from=builder /opt/venv /opt/venv

# Активируем виртуальное окружение
ENV PATH="/opt/venv/bin:$PATH"

# Переменные окружения приложения (можно переопределить при запуске)
ENV APP_NAME="devops-portfolio-app"
ENV APP_VERSION="0.1.0"
ENV LOG_LEVEL="INFO"

# Рабочая директория в контейнере
WORKDIR /app

# Копируем только код приложения (не .git, не тесты в образ)
COPY app/ /app/app/
COPY src/ /app/src/

# Создаём непривилегированного пользователя (security best practice)
# Никогда не запускайте приложение от root в контейнере!
RUN groupadd -r appuser && useradd -r -g appuser appuser
USER appuser

# Expose порт (это информационное, на самом деле не ограничивает)
EXPOSE 8000

# Health check (опционально, но полезно для Docker Compose)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz')" || exit 1

# Команда запуска приложения
# Используем exec-форму (список), а не shell-форму (строка)
# Это важно для корректной обработки сигналов (SIGTERM для graceful shutdown)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]