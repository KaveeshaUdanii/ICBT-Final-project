def test_blockchain_grows_and_stays_valid(client, auth_headers):
    resp = client.get("/api/blockchain/verify", headers=auth_headers)
    assert resp.status_code == 200
    before = resp.json()
    assert before["is_valid"] is True

    client.post(
        "/api/suppliers",
        headers=auth_headers,
        json={"name": "Chain Test Supplier", "contact_email": "chain@example.com"},
    )

    resp = client.get("/api/blockchain/verify", headers=auth_headers)
    after = resp.json()
    assert after["is_valid"] is True
    assert after["total_blocks"] > before["total_blocks"]


def test_blocks_are_hash_linked(client, auth_headers):
    resp = client.get("/api/blockchain/blocks?limit=5", headers=auth_headers)
    assert resp.status_code == 200
    blocks = resp.json()
    assert len(blocks) >= 2
    # blocks are returned newest-first; each one's previous_hash must equal the prior block's hash
    for i in range(len(blocks) - 1):
        newer, older = blocks[i], blocks[i + 1]
        assert newer["previous_hash"] == older["hash"]


def test_tampering_is_detected(client, auth_headers):
    from app.core.database import SessionLocal
    from app.models.blockchain import Block

    db = SessionLocal()
    try:
        first_block = db.query(Block).order_by(Block.block_index.asc()).first()
        first_block.payload = {**first_block.payload, "tampered": True}
        db.add(first_block)
        db.commit()
    finally:
        db.close()

    resp = client.get("/api/blockchain/verify", headers=auth_headers)
    result = resp.json()
    assert result["is_valid"] is False
    assert result["broken_at_index"] == 0


def test_smart_contract_rules_registered(client, auth_headers):
    resp = client.get("/api/blockchain/rules", headers=auth_headers)
    assert resp.status_code == 200
    rules = resp.json()
    assert len(rules) >= 5
    assert any(r["name"] == "High Supplier Risk Auto-Flag" for r in rules)
