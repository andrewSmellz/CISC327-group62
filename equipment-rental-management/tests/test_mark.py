# ============================================================
# TESTS FOR MARK'S ASSIGNED FEATURES
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

# View one renter
def test_view_one_renter(client):
    """Viewing a renter by id returns that renter and an unknown id returns 404."""
    john = client.post(
        "/renters", json={"name": "John Smith", "email": "john@example.com"}
    ).get_json()
    jane = client.post(
        "/renters", json={"name": "Jane Doe", "email": "jane@example.com"}
    ).get_json()

    response = client.get(f"/renters/{john['id']}")
    assert response.status_code == 200
    assert response.get_json() == john

    response = client.get(f"/renters/{jane['id']}")
    assert response.status_code == 200
    assert response.get_json() == jane

    # An id that doesn't exist returns a 404 error
    response = client.get("/renters/999")
    assert response.status_code == 404
    assert response.get_json() == {"error": "Renter not found"}

# Update renter
def test_update_renter(client):
    """Updating a renter changes only the given fields and the change is saved."""
    john = client.post(
        "/renters", json={"name": "John Smith", "email": "john@example.com"}
    ).get_json()
    jane = client.post(
        "/renters", json={"name": "Jane Doe", "email": "jane@example.com"}
    ).get_json()

    response = client.put(
        f"/renters/{john['id']}", json={"email": "john.smith@example.com"}
    )
    assert response.status_code == 200
    updated = response.get_json()
    assert updated["email"] == "john.smith@example.com"
    assert updated["name"] == "John Smith" 
    assert updated["id"] == john["id"]
    assert updated["membership_date"] == john["membership_date"]

    assert client.get(f"/renters/{john['id']}").get_json() == updated
    assert client.get(f"/renters/{jane['id']}").get_json() == jane

    # Updating an id that doesn't exist returns a 404 error
    response = client.put("/renters/999", json={"name": "Nobody"})
    assert response.status_code == 404
    assert response.get_json() == {"error": "Renter not found"}

# Delete renter
def test_delete_renter(client):
    """Deleting a renter removes only that renter, and an unknown id returns 404."""
    john = client.post(
        "/renters", json={"name": "John Smith", "email": "john@example.com"}
    ).get_json()
    jane = client.post(
        "/renters", json={"name": "Jane Doe", "email": "jane@example.com"}
    ).get_json()

    response = client.delete(f"/renters/{john['id']}")
    assert response.status_code == 204

    response = client.get(f"/renters/{john['id']}")
    assert response.status_code == 404
    assert client.get("/renters").get_json() == [jane]

    # Deleting John again (or any unknown id) returns 404
    response = client.delete(f"/renters/{john['id']}")
    assert response.status_code == 404
    assert response.get_json() == {"error": "Renter not found"}

# Return rented equipment
def test_return_rented_equipment(client):
    """Returning a rental records the return date and frees up the unit."""
    renter = client.post(
        "/renters", json={"name": "John Smith", "email": "john@example.com"}
    ).get_json()
    equipment = client.post(
        "/equipment", json={"name": "Chainsaw", "category": "Tools", "total_units": 2}
    ).get_json()
    rental = client.post(
        "/rentals", json={"equipment_id": equipment["id"], "renter_id": renter["id"]}
    ).get_json()

    availability = client.get(f"/equipment/{equipment['id']}/availability").get_json()
    assert availability["available_units"] == 1
    assert rental["return_date"] is None

    response = client.put(f"/rentals/{rental['id']}/return")
    assert response.status_code == 200
    returned = response.get_json()
    assert returned["return_date"] == date.today().isoformat()

    availability = client.get(f"/equipment/{equipment['id']}/availability").get_json()
    assert availability["available_units"] == 2

    # Returning the same rental twice is not allowed and doesn't add another unit
    response = client.put(f"/rentals/{rental['id']}/return")
    assert response.status_code == 400
    assert response.get_json() == {"error": "Rental already returned"}
    availability = client.get(f"/equipment/{equipment['id']}/availability").get_json()
    assert availability["available_units"] == 2

    # Returning a rental that doesn't exist returns 404
    response = client.put("/rentals/999/return")
    assert response.status_code == 404
    assert response.get_json() == {"error": "Rental not found"}

# Look up rentals
def test_look_up_rentals(client):
    """Rentals can be looked up by equipment and by renter."""
    john = client.post(
        "/renters", json={"name": "John Smith", "email": "john@example.com"}
    ).get_json()
    jane = client.post(
        "/renters", json={"name": "Jane Doe", "email": "jane@example.com"}
    ).get_json()
    chainsaw = client.post(
        "/equipment", json={"name": "Chainsaw", "category": "Tools", "total_units": 1}
    ).get_json()
    jackhammer = client.post(
        "/equipment", json={"name": "Jackhammer", "category": "Construction", "total_units": 1}
    ).get_json()

    john_rental = client.post(
        "/rentals", json={"equipment_id": jackhammer["id"], "renter_id": john["id"]}
    ).get_json()
    jane_rental = client.post(
        "/rentals", json={"equipment_id": chainsaw["id"], "renter_id": jane["id"]}
    ).get_json()

    response = client.get("/rentals")
    assert response.status_code == 200
    assert len(response.get_json()) == 2

    # Look up by equipment
    response = client.get(f"/rentals?equipment_id={chainsaw['id']}")
    assert response.status_code == 200
    assert response.get_json() == [jane_rental]

    # Look up by renter 
    response = client.get(f"/rentals?renter_id={john['id']}")
    assert response.status_code == 200
    assert response.get_json() == [john_rental] # Assertion fails due to line 17 in routes/rentals.py