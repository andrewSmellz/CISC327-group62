from unittest.mock import patch
 
import pytest
from app import store


#helpers for testing
def make_equipment(client, name="Tent", total_units=2):
    return client.post(
        "/equipment",
        json={"name": name, "category": "Camping", "total_units": total_units},
    ).get_json()

 
def make_rental(client, name="John Smith", email="john@example.com"):
    item = make_equipment(client)
    renter = client.post("/renters", json={"name": name, "email": email}).get_json()
    rental = client.post(
        "/rentals", json={"equipment_id": item["id"], "renter_id": renter["id"]}
    ).get_json()
    return item, renter, rental


def get_rental(client, rental_id):
    return next(r for r in client.get("/rentals").get_json() if r["id"] == rental_id)

 
# ------------------------------------------------------------
# notification failure and non-trigger paths
# ------------------------------------------------------------
def test_return_reminder_failure_does_not_mark_rental(client, monkeypatch):
    """send_notification fails, so the response says not sent and
       the rental is not marked as reminded."""
    monkeypatch.setattr(
        "app.routes.rentals.send_notification",
        lambda recipient, subject, message: False,
    )
    _, _, rental = make_rental(client)
 
    response = client.post(f"/rentals/{rental['id']}/reminder")
 
    assert response.status_code == 200
    assert response.get_json() == {"rental_id": rental["id"], "reminder_sent": False}
    assert get_rental(client, rental["id"])["reminder_sent"] is False
 
 
def test_return_reminder_unknown_rental_sends_nothing(client):
    """unknown rental returns 404 and send_notification is not called."""
    with patch("app.routes.rentals.send_notification") as mock_send:
        response = client.post("/rentals/999/reminder")
 
    assert response.status_code == 404
    assert response.get_json() == {"error": "Rental not found"}
    mock_send.assert_not_called()
 
 
def test_return_reminder_returned_rental_sends_nothing(client):
    """an already returned rental returns 400 and send_notification is not called."""
    _, _, rental = make_rental(client)
    client.put(f"/rentals/{rental['id']}/return")
 
    with patch("app.routes.rentals.send_notification") as mock_send:
        response = client.post(f"/rentals/{rental['id']}/reminder")
 
    assert response.status_code == 400
    assert response.get_json() == {"error": "Rental already returned"}
    mock_send.assert_not_called()
    assert get_rental(client, rental["id"])["reminder_sent"] is False
 
 
 