from __future__ import annotations

from httpx import AsyncClient


async def _customer(client: AsyncClient) -> int:
    response = await client.post(
        "/customers",
        json={"name": "Asha", "phone": "9876543210", "pincode": "110001"},
    )
    assert response.status_code == 201
    return int(response.json()["id"])


async def _technician(
    client: AsyncClient, *, active: bool = True, phone: str = "9123456780"
) -> int:
    response = await client.post(
        "/technicians",
        json={"name": "Ravi", "phone": phone, "active": active},
    )
    assert response.status_code == 201
    return int(response.json()["id"])


async def test_ticket_flow_and_invalid_jump(client: AsyncClient) -> None:
    customer_id = await _customer(client)
    tech_id = await _technician(client)
    created = await client.post(
        "/tickets",
        json={
            "customer_id": customer_id,
            "device": "Fan",
            "issue": "Noisy",
            "quoted_price": "499.00",
        },
    )
    assert created.status_code == 201
    ticket_id = created.json()["id"]
    assert created.json()["status"] == "NEW"

    bad = await client.post(f"/tickets/{ticket_id}/status", json={"status": "READY"})
    assert bad.status_code == 409

    assigned = await client.post(f"/tickets/{ticket_id}/assign", json={"technician_id": tech_id})
    assert assigned.status_code == 200
    assert assigned.json()["status"] == "ASSIGNED"
    assert assigned.json()["technician_id"] == tech_id

    for status in ("IN_REPAIR", "READY", "DELIVERED"):
        moved = await client.post(f"/tickets/{ticket_id}/status", json={"status": status})
        assert moved.status_code == 200
        assert moved.json()["status"] == status

    cancel = await client.post(f"/tickets/{ticket_id}/cancel")
    assert cancel.status_code == 409


async def test_cancel_from_new(client: AsyncClient) -> None:
    customer_id = await _customer(client)
    created = await client.post(
        "/tickets",
        json={"customer_id": customer_id, "device": "Iron", "issue": "Cold"},
    )
    ticket_id = created.json()["id"]
    cancelled = await client.post(f"/tickets/{ticket_id}/cancel")
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "CANCELLED"


async def test_inactive_technician(client: AsyncClient) -> None:
    customer_id = await _customer(client)
    tech_id = await _technician(client, active=False)
    ticket_id = (
        await client.post(
            "/tickets",
            json={"customer_id": customer_id, "device": "TV", "issue": "Blank"},
        )
    ).json()["id"]
    response = await client.post(f"/tickets/{ticket_id}/assign", json={"technician_id": tech_id})
    assert response.status_code == 409


async def test_missing_ticket(client: AsyncClient) -> None:
    response = await client.get("/tickets/404")
    assert response.status_code == 404


async def test_list_filters(client: AsyncClient) -> None:
    customer_id = await _customer(client)
    await client.post(
        "/tickets",
        json={"customer_id": customer_id, "device": "Fan", "issue": "A"},
    )
    listed = await client.get("/tickets", params={"customer_id": customer_id, "limit": 10})
    assert listed.status_code == 200
    assert len(listed.json()) == 1
