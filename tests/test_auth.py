"""Tests for authentication — login success, wrong password, unknown user."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, seeded_db):
    resp = await client.post("/login", json={"username": "testadmin", "password": "testpass"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["role"] == "admin"
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, seeded_db):
    resp = await client.post("/login", json={"username": "testadmin", "password": "wrongpass"})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid credentials"


@pytest.mark.asyncio
async def test_login_unknown_user(client: AsyncClient, seeded_db):
    resp = await client.post("/login", json={"username": "ghost", "password": "any"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_ask_without_token(client: AsyncClient):
    resp = await client.post("/ask", json={"session_id": "s1", "question": "hello"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
