from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["project"] == "LoopLens"


def test_summary() -> None:
    response = client.get("/api/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_loops" in data
    assert "review_label_distribution" in data


def test_loops_returns_rows_if_data_exists() -> None:
    summary = client.get("/api/summary").json()
    response = client.get("/api/loops?limit=5")
    assert response.status_code == 200
    rows = response.json()
    if summary.get("total_loops", 0) > 0:
        assert len(rows) > 0
        assert "participant_names" in rows[0]
        assert isinstance(rows[0]["participant_names"], list)
        assert "participants" in rows[0]


def test_loop_network() -> None:
    rows = client.get("/api/loops?limit=1").json()
    if not rows:
        return
    loop_id = str(rows[0].get("loop_id") or rows[0].get("id"))
    response = client.get(f"/api/loops/{loop_id}/network")
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert "nodes" in data
    assert "edges" in data
    assert "highlight_circular_path" in data
    if data["nodes"]:
        assert data["nodes"][0]["label"]
        assert data["nodes"][0].get("bn") or data["nodes"][0]["metadata"].get("bn")
        assert "total_sent" in data["nodes"][0]
        assert "total_received" in data["nodes"][0]
    if data["edges"]:
        assert "source_name" in data["edges"][0]
        assert "target_name" in data["edges"][0]
        assert "amount" in data["edges"][0]


def test_loop_detail_includes_organization_names() -> None:
    response = client.get("/api/loops/227")
    assert response.status_code == 200
    data = response.json()
    names = data["loop"].get("participant_names") or []
    if names:
        assert "VANCOUVER FOUNDATION" in names
    people = data.get("people") or []
    if people:
        assert people[0].get("name")
        assert "sends_to_bn" in people[0]
        assert "receives_from_bn" in people[0]


def test_loop_search_matches_participant_name() -> None:
    response = client.get("/api/loops?search=VANCOUVER%20FOUNDATION&limit=5")
    assert response.status_code == 200
    rows = response.json()
    if rows:
        assert any("VANCOUVER FOUNDATION" in row.get("participant_names", []) for row in rows)


def test_chat_worst_loop_returns_grounded_loop() -> None:
    response = client.post("/api/chat", json={"message": "what is the worst loop"})
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] in {"worst_loop", "top_loops"}
    assert data["intent"] != "unsupported"
    assert "loop" in data["answer"].lower() or "review score" in data["answer"].lower()
    assert "organizations" in data["answer"].lower() or "entities" in data["answer"].lower()
    assert "{" not in data["answer"]
    assert "}" not in data["answer"]
    assert "['" not in data["answer"]
    assert data.get("selected_loop_id")
    assert data.get("participants")
    assert len(data["participants"]) > 0
    assert any(
        row.get("organization_name") or row.get("legal_name") or row.get("account_name") or row.get("name") or row.get("bn")
        for row in data["participants"]
    )
    assert any(
        str(row.get("organization_name") or row.get("legal_name") or row.get("account_name") or row.get("name") or row.get("bn")) in data["answer"]
        for row in data["participants"]
    )
    assert data["data"]
    assert data["data"][0].get("loop_id") or data["data"][0].get("id")
    assert data["evidence"] == data["participants"]


def test_chat_company_details_returns_human_readable_entities() -> None:
    response = client.post("/api/chat", json={"message": "which companies are involved", "selected_loop_id": "227"})
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "selected_loop_participants"
    assert "organizations" in data["answer"].lower() or "entities" in data["answer"].lower()
    assert "role:" in data["answer"].lower()
    assert "{" not in data["answer"]
    assert data["data"]
    assert data["participants"]
    assert data["selected_loop_id"] == "227"


def test_chat_unsupported_has_no_fake_data_and_unsupported_verification() -> None:
    response = client.post("/api/chat", json={"message": "write me a recipe for pancakes"})
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "unsupported"
    assert data["data"] == []
    assert data["verification"]["overall_status"] == "Unsupported"


def test_route_intent_worst_loop_phrases() -> None:
    from src.chat import route_intent

    assert route_intent("what is the worst loop") == "worst_loop"
    assert route_intent("riskiest loop") == "worst_loop"
    assert route_intent("highest priority loop") == "worst_loop"


def test_backend_imports_do_not_load_legacy_ui_modules() -> None:
    import sys
    import src.chat
    import src.graph

    assert "streamlit" not in sys.modules
    assert "plotly" not in sys.modules
    assert "networkx" not in sys.modules
