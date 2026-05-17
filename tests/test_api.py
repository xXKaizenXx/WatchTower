import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_create_and_ping_service(client: AsyncClient, api_headers: dict):
    create_resp = await client.post(
        "/api/v1/services",
        json={
            "name": "Nightly ETL",
            "environment": "production",
            "heartbeat_interval": 3600,
            "grace_period": 300,
        },
        headers=api_headers,
    )
    assert create_resp.status_code == 201
    body = create_resp.json()
    service_id = body["id"]
    ping_token = body["ping_token"]
    assert ping_token

    ping_resp = await client.post(
        f"/ping/{service_id}",
        headers={"X-Ping-Token": ping_token},
    )
    assert ping_resp.status_code == 200
    assert ping_resp.json()["status"] == "HEALTHY"
    assert ping_resp.json()["last_ping_at"] is not None


@pytest.mark.asyncio
async def test_ping_rejects_invalid_token(client: AsyncClient, api_headers: dict):
    create_resp = await client.post(
        "/api/v1/services",
        json={"name": "Worker", "heartbeat_interval": 60},
        headers=api_headers,
    )
    service_id = create_resp.json()["id"]

    ping_resp = await client.post(
        f"/ping/{service_id}",
        headers={"X-Ping-Token": "invalid-token"},
    )
    assert ping_resp.status_code == 403


@pytest.mark.asyncio
async def test_services_require_api_key(client: AsyncClient):
    response = await client.get("/api/v1/services")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_incidents_empty(client: AsyncClient, api_headers: dict):
    response = await client.get("/api/v1/incidents", headers=api_headers)
    assert response.status_code == 200
    assert response.json() == []
