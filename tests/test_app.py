"""
Тесты для FastAPI приложения.

Используем pytest + TestClient из fastapi.testclient.
Каждый тест проверяет один эндпоинт и один сценарий.

Цель тестов на этой фазе: убедиться, что код ломается, когда мы что-то меняем.
Не полное покрытие, а скорее smoke-тесты.
"""

import pytest
from fastapi.testclient import TestClient

# Импортируем приложение
from app.main import app

# TestClient оборачивает FastAPI-приложение для синхронного тестирования
client = TestClient(app)


class TestRoot:
    """Тесты для эндпоинта GET /"""
    
    def test_root_returns_200(self):
        """Проверяем, что / возвращает 200 OK."""
        response = client.get("/")
        assert response.status_code == 200
    
    def test_root_returns_json(self):
        """Проверяем, что / возвращает JSON с нужными полями."""
        response = client.get("/")
        data = response.json()
        
        # Проверяем наличие обязательных полей
        assert "name" in data
        assert "version" in data
        assert "status" in data
        
        # Проверяем значения
        assert data["status"] == "ok"
    
    def test_root_has_version(self):
        """Проверяем, что версия не пустая."""
        response = client.get("/")
        data = response.json()
        assert data["version"] != ""


class TestHealthz:
    """Тесты для эндпоинта GET /healthz (liveness probe)"""
    
    def test_healthz_returns_200(self):
        """Проверяем, что /healthz всегда возвращает 200."""
        response = client.get("/healthz")
        assert response.status_code == 200
    
    def test_healthz_returns_status_alive(self):
        """Проверяем, что /healthz возвращает status: alive."""
        response = client.get("/healthz")
        data = response.json()
        assert data["status"] == "alive"


class TestReadyz:
    """Тесты для эндпоинта GET /readyz (readiness probe)"""
    
    def test_readyz_returns_200_when_ready(self):
        """Проверяем, что /readyz возвращает 200, когда приложение готово."""
        # Убедимся, что приложение в состоянии "ready"
        client.post("/set-ready/true")
        
        response = client.get("/readyz")
        assert response.status_code == 200
        assert response.json()["status"] == "ready"
    
    def test_readyz_returns_503_when_not_ready(self):
        """Проверяем, что /readyz возвращает 503, когда приложение не готово."""
        # Переключим приложение в состояние "not ready"
        client.post("/set-ready/false")
        
        response = client.get("/readyz")
        assert response.status_code == 503
    
    def test_readyz_state_can_be_toggled(self):
        """Проверяем, что состояние можно менять через /set-ready."""
        # Сначала сделаем не готовым
        response1 = client.post("/set-ready/false")
        assert response1.json()["ready"] is False
        
        # Проверяем, что readyz вернёт 503
        assert client.get("/readyz").status_code == 503
        
        # Теперь сделаем готовым
        response2 = client.post("/set-ready/true")
        assert response2.json()["ready"] is True
        
        # Проверяем, что readyz вернёт 200
        assert client.get("/readyz").status_code == 200


class TestIntegration:
    """Интеграционные тесты (несколько эндпоинтов вместе)"""
    
    def test_full_startup_flow(self):
        """
        Имитируем полный цикл загрузки приложения:
        1. Приложение стартует (healthz уже работает)
        2. Приложение инициализируется (readyz становится 200)
        3. Приложение обслуживает трафик (root работает)
        """
        # После старта healthz всегда должен работать
        assert client.get("/healthz").status_code == 200
        
        # Убедимся, что readyz готов
        client.post("/set-ready/true")
        assert client.get("/readyz").status_code == 200
        
        # Корневой эндпоинт должен работать
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"