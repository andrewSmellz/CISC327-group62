# ============================================================
# TESTS for Mark's assigned features
# ============================================================
from datetime import date

# Add renter
def test_add_renter(client):
    """Adding a renter returns its data and stores it in the system."""
    response = client.post(
        "/renters",
        json={"name": "John Smith", "email": "john@example.com"},
    )

    assert response.status_code == 201
    renter = response.get_json()
    assert renter["name"] == "John Smith"
    assert renter["email"] == "john@example.com"
    assert renter["membership_date"] == date.today().isoformat()

    get_resp = client.get(f"/renters/{renter['id']}")
    assert get_resp.status_code == 200
    assert get_resp.get_json() == renter

# List renters
def test_list_renters(client):
    """Listing renters returns every renter that has been added."""
    response = client.get("/renters")
    assert response.status_code == 200
    assert response.get_json() == []

    first = client.post(
        "/renters", json={"name": "John Smith", "email": "john@example.com"}
    ).get_json()
    second = client.post(
        "/renters", json={"name": "Jane Doe", "email": "jane@example.com"}
    ).get_json()

    response = client.get("/renters")
    assert response.status_code == 200
    renters = response.get_json()
    assert len(renters) == 2
    assert first in renters
    assert second in renters