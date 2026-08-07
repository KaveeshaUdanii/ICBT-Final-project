def test_create_and_list_supplier(client, auth_headers):
    resp = client.post(
        "/api/suppliers",
        headers=auth_headers,
        json={
            "name": "Pytest Fabric Co",
            "contact_email": "contact@pytestfabric.com",
            "category": "fabric",
            "on_time_delivery_rate": 0.7,
            "defect_rate": 0.08,
            "cancellation_rate": 0.05,
            "avg_lead_time_days": 20,
            "order_volume_last_year": 60,
        },
    )
    assert resp.status_code == 201
    supplier = resp.json()
    assert supplier["risk_score"] == 0.0  # not scored yet

    resp = client.get("/api/suppliers", headers=auth_headers)
    assert resp.status_code == 200
    assert any(s["name"] == "Pytest Fabric Co" for s in resp.json())


def test_update_and_delete_supplier(client, auth_headers):
    resp = client.post(
        "/api/suppliers",
        headers=auth_headers,
        json={"name": "Temp Supplier", "contact_email": "temp@example.com"},
    )
    supplier_id = resp.json()["id"]

    resp = client.put(
        f"/api/suppliers/{supplier_id}", headers=auth_headers, json={"country": "Vietnam"}
    )
    assert resp.status_code == 200
    assert resp.json()["country"] == "Vietnam"

    resp = client.delete(f"/api/suppliers/{supplier_id}", headers=auth_headers)
    assert resp.status_code == 204

    resp = client.get(f"/api/suppliers/{supplier_id}", headers=auth_headers)
    assert resp.status_code == 404


def test_raw_material_reorder_flag(client, auth_headers):
    resp = client.post(
        "/api/suppliers",
        headers=auth_headers,
        json={"name": "Material Supplier", "contact_email": "mat@example.com"},
    )
    supplier_id = resp.json()["id"]

    resp = client.post(
        "/api/raw-materials",
        headers=auth_headers,
        json={
            "name": "Low Stock Item",
            "category": "fabric",
            "quantity_on_hand": 10,
            "reorder_level": 50,
            "supplier_id": supplier_id,
        },
    )
    assert resp.status_code == 201
    assert resp.json()["needs_reorder"] is True

    resp = client.get("/api/recommendations", headers=auth_headers)
    assert any(r["entity_type"] == "raw_material" for r in resp.json())
