from __future__ import annotations

import httpx
from httpx import AsyncClient


async def test_create_and_get_customer(client: AsyncClient) -> None:
    created = await client.post(
        "/customers",
        json={"name": "Asha", "phone": "9876543210", "pincode": "110001"},
    )
    assert created.status_code == 201
    body = created.json()
    assert body["district"] == "New Delhi"
    assert "request_id" not in body
    customer_id = body["id"]

    fetched = await client.get(f"/customers/{customer_id}")
    assert fetched.status_code == 200
    assert fetched.json()["phone"] == "9876543210"
    assert fetched.headers["x-request-id"]


async def test_missing_customer(client: AsyncClient) -> None:
    response = await client.get("/customers/9999")
    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "NOT_FOUND"
    assert error["request_id"]


async def test_bad_phone(client: AsyncClient) -> None:
    response = await client.post(
        "/customers",
        json={"name": "Asha", "phone": "12345", "pincode": "110001"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_duplicate_phone(client: AsyncClient) -> None:
    payload = {"name": "Asha", "phone": "9876543210", "pincode": "110001"}
    assert (await client.post("/customers", json=payload)).status_code == 201
    dup = await client.post("/customers", json={**payload, "name": "Other"})
    assert dup.status_code == 409
    assert dup.json()["error"]["code"] == "CONFLICT"


async def test_out_of_area_pincode(client: AsyncClient) -> None:
    response = await client.post(
        "/customers",
        json={"name": "Asha", "phone": "9876543210", "pincode": "560001"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "PINCODE_OUT_OF_AREA"


async def test_unknown_pincode(client: AsyncClient) -> None:
    response = await client.post(
        "/customers",
        json={"name": "Asha", "phone": "9876543210", "pincode": "000000"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "PINCODE_NOT_FOUND"


async def test_cannot_delete_with_open_ticket(client: AsyncClient) -> None:
    customer = (
        await client.post(
            "/customers",
            json={"name": "Asha", "phone": "9876543210", "pincode": "110001"},
        )
    ).json()
    await client.post(
        "/tickets",
        json={"customer_id": customer["id"], "device": "Mixer", "issue": "Sparking"},
    )
    response = await client.delete(f"/customers/{customer['id']}")
    assert response.status_code == 409


async def test_pydantic_runs_before_handler(client: AsyncClient) -> None:
    """422 for {'phone': '12345'} is produced by Pydantic, before the route body."""
    response = await client.post("/customers", json={"phone": "12345"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_pincode_timeout_is_504(client: AsyncClient, mock_pincode_api: object) -> None:
    mock_pincode_api.get("https://api.postalpincode.in/pincode/110001").mock(  # type: ignore[union-attr]
        side_effect=httpx.TimeoutException("slow")
    )
    response = await client.post(
        "/customers",
        json={"name": "Asha", "phone": "9876543210", "pincode": "110001"},
    )
    assert response.status_code == 504
    assert response.json()["error"]["code"] == "UPSTREAM_TIMEOUT"


async def test_pincode_500_is_502(client: AsyncClient, mock_pincode_api: object) -> None:
    mock_pincode_api.get("https://api.postalpincode.in/pincode/110001").mock(  # type: ignore[union-attr]
        return_value=httpx.Response(500, text="down")
    )
    response = await client.post(
        "/customers",
        json={"name": "Asha", "phone": "9876543210", "pincode": "110001"},
    )
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "UPSTREAM_ERROR"
