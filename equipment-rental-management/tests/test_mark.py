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