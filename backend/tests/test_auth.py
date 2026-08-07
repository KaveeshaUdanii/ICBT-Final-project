def test_register_and_login(client):
    resp = client.post(
        "/api/auth/register",
        json={"name": "Jane Manager", "email": "jane@example.com", "password": "password123", "role": "supply_chain_manager"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["user"]["email"] == "jane@example.com"
    assert body["user"]["role"] == "supply_chain_manager"

    resp = client.post("/api/auth/login", json={"email": "jane@example.com", "password": "password123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_wrong_password_rejected(client):
    client.post(
        "/api/auth/register",
        json={"name": "Bob", "email": "bob@example.com", "password": "correcthorse", "role": "supply_chain_manager"},
    )
    resp = client.post("/api/auth/login", json={"email": "bob@example.com", "password": "wrongpassword"})
    assert resp.status_code == 401


def test_protected_route_requires_token(client):
    resp = client.get("/api/suppliers")
    assert resp.status_code == 401


def test_duplicate_email_rejected(client):
    client.post(
        "/api/auth/register",
        json={"name": "Dup", "email": "dup@example.com", "password": "password123", "role": "supply_chain_manager"},
    )
    resp = client.post(
        "/api/auth/register",
        json={"name": "Dup2", "email": "dup@example.com", "password": "password123", "role": "supply_chain_manager"},
    )
    assert resp.status_code == 400


def test_role_based_access_control(client):
    resp = client.post(
        "/api/auth/register",
        json={"name": "Sam Supplier", "email": "sam-supplier@example.com", "password": "password123", "role": "supplier"},
    )
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # A supplier-role user cannot create a supplier record (manager/admin only).
    resp = client.post(
        "/api/suppliers",
        headers=headers,
        json={"name": "Should Fail Co", "contact_email": "x@x.com"},
    )
    assert resp.status_code == 403
