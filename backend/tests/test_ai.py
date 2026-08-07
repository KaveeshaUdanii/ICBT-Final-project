def _create_supplier(client, auth_headers, **overrides):
    payload = {
        "name": "AI Test Supplier",
        "contact_email": "aitest@example.com",
        "category": "fabric",
        "on_time_delivery_rate": 0.6,
        "defect_rate": 0.15,
        "cancellation_rate": 0.12,
        "avg_lead_time_days": 35,
        "order_volume_last_year": 15,
    }
    payload.update(overrides)
    resp = client.post("/api/suppliers", headers=auth_headers, json=payload)
    assert resp.status_code == 201
    return resp.json()


def test_supplier_risk_scoring_and_explanation(client, auth_headers):
    supplier = _create_supplier(client, auth_headers, name="Risky Supplier Co")
    resp = client.post(f"/api/ai/suppliers/{supplier['id']}/score", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert 0 <= body["risk_score"] <= 100
    assert body["risk_level"] in ("low", "medium", "high")
    explanation = body["explanation"]
    assert explanation["model_name"] == "supplier_risk_scoring"
    assert len(explanation["top_factors"]) >= 1
    for factor in explanation["top_factors"]:
        assert factor["direction"] in ("increases_risk", "decreases_risk")
        assert isinstance(factor["explanation"], str) and len(factor["explanation"]) > 0


def test_high_risk_supplier_triggers_notification(client, auth_headers):
    supplier = _create_supplier(
        client,
        auth_headers,
        name="Very Risky Supplier",
        on_time_delivery_rate=0.35,
        defect_rate=0.3,
        cancellation_rate=0.28,
        avg_lead_time_days=60,
        order_volume_last_year=5,
    )
    client.post(f"/api/ai/suppliers/{supplier['id']}/score", headers=auth_headers)

    resp = client.get("/api/notifications", headers=auth_headers)
    notifications = resp.json()
    assert any("Very Risky Supplier" in n["message"] for n in notifications)


def test_shipment_delay_prediction(client, auth_headers):
    supplier = _create_supplier(client, auth_headers, name="Shipment Test Supplier")
    resp = client.post(
        "/api/shipments",
        headers=auth_headers,
        json={
            "shipment_code": "SHP-TEST-001",
            "supplier_id": supplier["id"],
            "quantity": 500,
            "expected_delivery_date": "2026-12-01",
        },
    )
    assert resp.status_code == 201
    shipment_id = resp.json()["id"]

    resp = client.post(f"/api/ai/shipments/{shipment_id}/predict", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["predicted_delay_days"] >= 0
    assert 0 <= body["delay_probability"] <= 1
    assert isinstance(body["is_anomaly"], bool)


def test_model_performance_report(client, auth_headers):
    resp = client.get("/api/ai/model-performance", headers=auth_headers)
    assert resp.status_code == 200
    report = resp.json()
    for key in ("supplier_risk_scoring_model", "delay_prediction_model", "anomaly_detection_model"):
        assert key in report


def test_scenario_simulation(client, auth_headers):
    supplier = _create_supplier(client, auth_headers, name="Scenario Supplier")
    resp = client.post(
        "/api/scenarios/simulate",
        headers=auth_headers,
        json={
            "name": "Test Scenario",
            "scenario_type": "supplier_failure",
            "input_params": {"supplier_id": supplier["id"], "severity": 0.5},
        },
    )
    assert resp.status_code == 200
    result = resp.json()["result"]
    assert "simulated_risk_score" in result
    assert "recommendation" in result
