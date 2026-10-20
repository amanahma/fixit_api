from httpx import AsyncClient


async def test_health(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_unhandled_is_generic_500(client: AsyncClient) -> None:
    response = await client.get("/debug/boom")
    assert response.status_code == 500
    error = response.json()["error"]
    assert error["code"] == "INTERNAL_ERROR"
    assert error["message"] == "An unexpected error occurred"
    assert "RuntimeError" not in error["message"]
    assert error["request_id"]
