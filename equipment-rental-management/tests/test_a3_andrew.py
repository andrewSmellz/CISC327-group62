from unittest.mock import patch
 
import pytest
from app import store


#helpers for testing
def make_equipment(client, name="Tent", total_units=2):
    return client.post(
        "/equipment",
        json={"name": name, "category": "Camping", "total_units": total_units},
    ).get_json()

 
def make_rental(client, name="John doe", email="johndoe@example.com"):
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
 
 
# ------------------------------------------------------------
# coverage-directed tests for app/routes/views.py
# ------------------------------------------------------------
def test_home_page_renders(client):
    """the html properly renders"""
    response = client.get("/")
    assert response.status_code == 200
    assert b"<html" in response.data.lower()
 
 
# equipment_page and delete_equipment_page
def test_equipment_page_lists_existing_equipment(client):
    """the equipment page shows equipment that already exists."""
    make_equipment(client, name="Canoe")
 
    response = client.get("/ui/equipment")
 
    assert response.status_code == 200
    assert b"Canoe" in response.data
 
 
def test_equipment_page_adds_equipment(client):
    """posting the add equipment form creates the item with all units available."""
    response = client.post(
        "/ui/equipment",
        data={"name": "sleeping bag", "category": "Camping", "total_units": "3"},
    )
 
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/ui/equipment")
    item = next(iter(store.equipment.values()))
    assert (item.name, item.category) == ("sleeping bag", "Camping")
    assert item.total_units == 3
    assert item.available_units == 3
 
 
def test_equipment_page_rejects_non_numeric_units(client):
    """a non-integer total_units raises ValueError and no equipment is created."""
    with pytest.raises(ValueError):
        client.post(
            "/ui/equipment",
            data={"name": "Tent", "category": "Camping", "total_units": "failure"},
        )
    assert store.equipment == {}
 
 
def test_delete_equipment_page_removes_item(client):
    """deleting through the page removes the item and nothing else."""
    drop = make_equipment(client, name="DropMe")
    keep = make_equipment(client, name="KeepMe")
 
    response = client.post(f"/ui/equipment/{drop['id']}/delete")
 
    assert response.status_code == 302
    assert list(store.equipment) == [keep["id"]]
 
 
def test_delete_equipment_page_unknown_id_is_harmless(client):
    """deleting an id that does not exist does nothing."""
    item = make_equipment(client)
 
    response = client.post("/ui/equipment/999/delete")
 
    assert response.status_code == 302
    assert list(store.equipment) == [item["id"]]
 
 
# renters_page and delete_renter_page
def test_renters_page_lists_existing_renters(client):
    """the renters page shows renters that already exist."""
    make_rental(client, name="john doe", email="johndoe@example.com")
 
    response = client.get("/ui/renters")
 
    assert response.status_code == 200
    assert b"john doe" in response.data
 
 
def test_renters_page_adds_renter(client):
    """posting the form creates the renter."""
    response = client.post(
        "/ui/renters", data={"name": "john doe", "email": "johndoe@example.com"}
    )
 
    assert response.status_code == 302
    renter = next(iter(store.renters.values()))
    assert (renter.name, renter.email) == ("john doe", "johndoe@example.com")
 
 
def test_delete_renter_page_removes_renter(client):
    """deleting through the form removes the renter."""
    _, renter, _ = make_rental(client)
 
    response = client.post(f"/ui/renters/{renter['id']}/delete")
 
    assert response.status_code == 302
    assert store.renters == {}
 
 
def test_delete_renter_page_unknown_id_is_harmless(client):
    """deleting an id that does not exist removes nothing."""
    _, renter, _ = make_rental(client)
 
    response = client.post("/ui/renters/999/delete")
 
    assert response.status_code == 302
    assert list(store.renters) == [renter["id"]]
 
 
def test_rentals_page_lists_existing_rentals(client):
    """the rentals page loads existing rentals."""
    _, _, rental = make_rental(client)
 
    response = client.get("/ui/rentals")
 
    assert response.status_code == 200
    assert rental["due_date"].encode() in response.data
 
 
