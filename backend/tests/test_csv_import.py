import io


def _csv_file(content: str, filename: str = "import.csv"):
    return {"file": (filename, io.BytesIO(content.encode("utf-8")), "text/csv")}


def test_suppliers_csv_import_success_and_partial_failure(client, auth_headers):
    csv_content = (
        "name,contact_email,country,category,on_time_delivery_rate\n"
        "Import Co A,importa@example.com,Vietnam,fabric,0.9\n"
        "Import Co B,importb@example.com,India,buttons,0.85\n"
        ",bad-email-no-at-sign,Pakistan,trims,0.8\n"  # missing required name + invalid email
    )
    resp = client.post("/api/suppliers/import-csv", headers=auth_headers, files=_csv_file(csv_content))
    assert resp.status_code == 200
    body = resp.json()
    assert body["imported"] == 2
    assert body["failed"] == 1
    assert len(body["errors"]) == 1
    assert body["errors"][0]["row"] == 4

    listed = client.get("/api/suppliers?q=Import Co", headers=auth_headers).json()
    names = {s["name"] for s in listed}
    assert "Import Co A" in names
    assert "Import Co B" in names


def test_csv_import_rejected_for_supplier_role(client):
    resp = client.post(
        "/api/auth/register",
        json={"name": "CSV Test Supplier", "email": "csv-supplier@example.com", "password": "password123", "role": "supplier"},
    )
    headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}

    csv_content = "name,contact_email\nShould Not Import,x@x.com\n"
    resp = client.post("/api/suppliers/import-csv", headers=headers, files=_csv_file(csv_content))
    assert resp.status_code == 403


def test_raw_materials_csv_import_resolves_supplier_by_name(client, auth_headers):
    supplier_resp = client.post(
        "/api/suppliers",
        headers=auth_headers,
        json={"name": "Material Import Test Supplier", "contact_email": "matimport@example.com"},
    )
    assert supplier_resp.status_code == 201

    csv_content = (
        "name,category,unit,quantity_on_hand,reorder_level,unit_cost,lead_time_days,supplier_name\n"
        "Import Test Fabric,fabric,meters,500,100,3.5,14,Material Import Test Supplier\n"
        "Import Test Bad,fabric,meters,200,50,2.0,10,No Such Supplier\n"
    )
    resp = client.post("/api/raw-materials/import-csv", headers=auth_headers, files=_csv_file(csv_content))
    assert resp.status_code == 200
    body = resp.json()
    assert body["imported"] == 1
    assert body["failed"] == 1
    assert "No Such Supplier" in body["errors"][0]["error"]

    materials = client.get("/api/raw-materials", headers=auth_headers).json()
    assert any(m["name"] == "Import Test Fabric" for m in materials)
