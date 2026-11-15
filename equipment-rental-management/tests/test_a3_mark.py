from datetime import date, timedelta
from unittest.mock import patch

import pytest

from app import store


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


def test_return_reminder_success_marks_rental_reminded(client, monkeypatch):
    monkeypatch.setattr(
        "app.routes.rentals.send_notification",
        lambda recipient, subject, message: True,
    )
    item, renter, rental = make_rental(client)
    assert rental["reminder_sent"] is False

    response = client.post(f"/rentals/{rental['id']}/reminder")

    assert response.status_code == 200
    assert response.get_json() == {"rental_id": rental["id"], "reminder_sent": True}
    stored = get_rental(client, rental["id"])
    assert stored["reminder_sent"] is True
    assert stored["return_date"] is None
    assert stored["due_date"] == rental["due_date"]


def test_return_reminder_sends_expected_notification(client):
    item, renter, rental = make_rental(client)

    with patch("app.routes.rentals.send_notification", return_value=True) as mock_send:
        response = client.post(f"/rentals/{rental['id']}/reminder")

    assert response.status_code == 200
    assert response.get_json()["reminder_sent"] is True
    assert get_rental(client, rental["id"])["reminder_sent"] is True
    mock_send.assert_called_once_with(
        "john@example.com",
        "Return reminder",
        f"Hi John Smith, please return Tent by {rental['due_date']}.",
    )


def test_return_reminder_goes_to_the_rentals_own_renter(client):
    first_item, first_renter, first_rental = make_rental(client)
    second_item, second_renter, second_rental = make_rental(
        client, name="Jane Doe", email="jane@example.com"
    )

    with patch("app.routes.rentals.send_notification", return_value=True) as mock_send:
        response = client.post(f"/rentals/{second_rental['id']}/reminder")

    assert response.get_json() == {
        "rental_id": second_rental["id"],
        "reminder_sent": True,
    }
    assert mock_send.call_count == 1
    assert mock_send.call_args.args[0] == "jane@example.com"
    assert "Jane Doe" in mock_send.call_args.args[2]
    assert get_rental(client, second_rental["id"])["reminder_sent"] is True
    assert get_rental(client, first_rental["id"])["reminder_sent"] is False


def test_update_equipment_changes_only_given_fields(client):
    item = make_equipment(client)
    other = make_equipment(client, name="Stove")

    response = client.put(
        f"/equipment/{item['id']}", json={"name": "Big Tent", "total_units": 5}
    )

    assert response.status_code == 200
    updated = response.get_json()
    assert updated["name"] == "Big Tent"
    assert updated["total_units"] == 5
    assert updated["category"] == item["category"]
    assert updated["available_units"] == item["available_units"]
    assert updated["is_available"] is True
    assert client.get(f"/equipment/{item['id']}").get_json() == updated
    assert client.get(f"/equipment/{other['id']}").get_json() == other


def test_update_equipment_unknown_id_returns_404(client):
    item = make_equipment(client)

    response = client.put("/equipment/999", json={"name": "Ghost"})

    assert response.status_code == 404
    assert response.get_json() == {"error": "Equipment not found"}
    assert client.get("/equipment").get_json() == [item]


def test_set_equipment_status_takes_item_out_of_service(client):
    item = make_equipment(client)

    response = client.patch(
        f"/equipment/{item['id']}/status", json={"is_available": False}
    )

    assert response.status_code == 200
    assert response.get_json()["is_available"] is False
    availability = client.get(f"/equipment/{item['id']}/availability").get_json()
    assert availability == {
        "equipment_id": item["id"],
        "is_available": False,
        "available_units": 2,
        "total_units": 2,
    }

    response = client.patch(
        f"/equipment/{item['id']}/status", json={"is_available": True}
    )
    assert response.get_json()["is_available"] is True


def test_set_equipment_status_unknown_id_returns_404(client):
    response = client.patch("/equipment/999/status", json={"is_available": False})

    assert response.status_code == 404
    assert response.get_json() == {"error": "Equipment not found"}


@pytest.mark.xfail(
    reason="checkout_equipment() ignores is_available, so out-of-service equipment can still be checked out"
)
def test_out_of_service_equipment_cannot_be_checked_out(client):
    item = make_equipment(client)
    client.patch(f"/equipment/{item['id']}/status", json={"is_available": False})

    response = client.post(
        "/rentals", json={"equipment_id": item["id"], "renter_id": 1}
    )

    assert response.status_code == 400
    assert client.get("/rentals").get_json() == []


def test_equipment_lookups_with_unknown_id_return_404(client):
    item = make_equipment(client)

    for response in (
        client.get("/equipment/999"),
        client.delete("/equipment/999"),
        client.get("/equipment/999/availability"),
        client.patch("/equipment/999/damage", json={"description": "Torn"}),
    ):
        assert response.status_code == 404
        assert response.get_json() == {"error": "Equipment not found"}

    assert client.get("/equipment").get_json() == [item]


def test_record_damage_without_description_is_rejected(client):
    item = make_equipment(client)

    for payload in ({}, {"description": ""}):
        response = client.patch(f"/equipment/{item['id']}/damage", json=payload)
        assert response.status_code == 400
        assert response.get_json() == {"error": "Description is required"}

    assert client.get(f"/equipment/{item['id']}").get_json()["damage_notes"] is None


def test_extend_rental_moves_due_date(client):
    item, renter, rental = make_rental(client)
    due = date.fromisoformat(rental["due_date"])

    response = client.put(f"/rentals/{rental['id']}/extend", json={"days": 3})

    assert response.status_code == 200
    assert response.get_json()["due_date"] == (due + timedelta(days=3)).isoformat()
    assert get_rental(client, rental["id"])["due_date"] == (
        due + timedelta(days=3)
    ).isoformat()


def test_extend_rental_defaults_to_one_day(client):
    item, renter, rental = make_rental(client)
    due = date.fromisoformat(rental["due_date"])

    response = client.put(f"/rentals/{rental['id']}/extend", json={})

    assert response.status_code == 200
    assert response.get_json()["due_date"] == (due + timedelta(days=1)).isoformat()


def test_extend_rental_rejects_unknown_and_returned_rentals(client):
    item, renter, rental = make_rental(client)

    response = client.put("/rentals/999/extend", json={"days": 3})
    assert response.status_code == 404
    assert response.get_json() == {"error": "Rental not found"}

    client.put(f"/rentals/{rental['id']}/return")
    response = client.put(f"/rentals/{rental['id']}/extend", json={"days": 3})
    assert response.status_code == 400
    assert response.get_json() == {"error": "Rental already returned"}
    assert get_rental(client, rental["id"])["due_date"] == rental["due_date"]


def test_release_deposit_rejects_unknown_and_unreturned_rentals(client):
    item, renter, rental = make_rental(client)

    response = client.put("/rentals/999/deposit/release")
    assert response.status_code == 404
    assert response.get_json() == {"error": "Rental not found"}

    response = client.put(f"/rentals/{rental['id']}/deposit/release")
    assert response.status_code == 400
    assert response.get_json() == {"error": "Equipment has not been returned yet"}
    assert get_rental(client, rental["id"])["deposit_released"] is False


@pytest.mark.xfail(
    reason="release_deposit() reports deposit_released true but never saves it on the rental"
)
def test_release_deposit_is_saved_on_the_rental(client):
    item, renter, rental = make_rental(client)
    client.put(f"/rentals/{rental['id']}/return")

    response = client.put(f"/rentals/{rental['id']}/deposit/release")

    assert response.status_code == 200
    assert response.get_json() == {"rental_id": rental["id"], "deposit_released": True}
    assert get_rental(client, rental["id"])["deposit_released"] is True


def test_days_overdue_boundaries(client):
    item, renter, rental = make_rental(client)
    stored = store.rentals[rental["id"]]
    today = date.today()

    stored.due_date = today
    assert stored.days_overdue() == 0
    assert client.get("/rentals/overdue").get_json() == []

    stored.due_date = today - timedelta(days=1)
    assert stored.days_overdue() == 1
    overdue = client.get("/rentals/overdue").get_json()
    assert [r["id"] for r in overdue] == [rental["id"]]
    assert overdue[0]["days_overdue"] == 1

    client.put(f"/rentals/{rental['id']}/return")
    assert stored.days_overdue() == 0