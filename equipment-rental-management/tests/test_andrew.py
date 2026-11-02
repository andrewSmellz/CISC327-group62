# ============================================================
# TESTS FOR ANDREW'S FEATURES 
# Features: add / list / view / update / delete equipment, checkout
# ============================================================

from datetime import date, timedelta



# ------------------------------------------------------------
# Add equipment 
# ------------------------------------------------------------
def test_add_equipment_returns_exepected_fields(client):
    """
    Adding equipment returns 201 and the new item with all expected fields.
    A new item starts with every unit available and in service.
    """
    payload = {
        "name": "Tent", 
        "category": "Camping", 
        "total_units": 4
    }
    response = client.post("/equipment", json=payload)
    assert response.status_code == 201
    item = response.get_json()
    assert isinstance(item["id"], int)
    assert item["name"] == "Tent"
    assert item["category"] == "Camping"
    assert item["total_units"] == 4
    assert item["available_units"] == 4
    assert item["is_available"] is True

def test_add_equipment_default_values_to_one(client):
    """
    total_units defaults to 1 when not given a value
    """
    payload = {
        "name": "canoe", 
        "category": "water", 
    }
    response = client.post("/equipment", json=payload)
    assert response.status_code == 201
    item = response.get_json()
    assert item["total_units"] == 1
    assert item["available_units"] == 1

def test_added_equipment_can_be_fetched(client):
    """a GET on a new item returns exactly what POST returned"""
    payload = {
        "name": "snow mobile", 
        "category": "winter",
        "total_units": 2 
    }
    response1 = client.post("/equipment", json=payload)
    created = response1.get_json()
    response2 = client.get(f"/equipment/{created['id']}")
    assert response2.status_code == 200
    assert response2.get_json() == created

def test_equipment_get_unique_id(client):
    """Multiple items added in a row recieve unique id's"""
    ids = set()
    for i in range(10):
        response = client.post("/equipment", json={"name": f"trowel {i}", "category": "camping"})
        assert response.status_code == 201
        ids.add(response.get_json()["id"])
    assert len(ids) == 10


def test_add_equipment_missing_category_expected_fail(client):
    """EXPECTED FAILURE: a missing field crashes the app (500) instead of returning a 4xx error."""
    response = client.post("/equipment", json={"name": "Tent"})
    assert response.status_code in (400, 422)
    assert client.get("/equipment").get_json() == []
 
 
def test_add_equipment_negative_units_expected_fail(client):
    """EXPECTED FAILURE: the app accepts total_units=-5 and available_units=-5."""
    payload = {"name": "sleeping bag", "category": "Camping", "total_units": -1}
    response = client.post("/equipment", json=payload)
    assert response.status_code in (400, 422)



# ------------------------------------------------------------
# List equipment 
# ------------------------------------------------------------
def test_list_equipment_returns_empty_list_initially(client):
    """The equipment list is initially empty before anything has been added."""
    response = client.get("/equipment")
    assert response.status_code == 200
    assert response.get_json() == []
 
 
def test_added_equipment_appears_in_list(client):
    """the new added item shows up in the equipment list properly."""
    payload = {"name": "Kayak", "category": "Water", "total_units": 2}
    created = client.post("/equipment", json=payload).get_json()
 
    response = client.get("/equipment")
    assert response.status_code == 200
    assert response.get_json() == [created]
 
 
def test_list_equipment_returns_all_items_in_order(client):
    """multiple added items all appear in the list, in the order they were added."""
    created = []
    for i in range(3):
        payload = {"name": f"Item {i}", "category": "MISC", "total_units": 1}
        created.append(client.post("/equipment", json=payload).get_json())
 
    response = client.get("/equipment")
    assert response.status_code == 200
    assert response.get_json() == created


#------------------------------------------------------------
# Delete equipment
# ------------------------------------------------------------
def test_delete_equipment_removes_it_from_list(client):
    """After a delete, the item no longer appears in the equipment list."""

    payload = {"name": "Tent", "category": "Camping", "total_units": 1}
    equipment_id = client.post("/equipment", json=payload).get_json()["id"]
 
    response = client.delete(f"/equipment/{equipment_id}")
    assert response.status_code == 204 
 
    # verify the item was actually removed
    assert client.get("/equipment").get_json() == []
 
 
def test_delete_equipment_only_removes_target(client):
    """Deleting one item leaves the other item untouched."""
    keep = client.post(
        "/equipment", json={"name": "KeepMe", "category": "MISC", "total_units": 1}
    ).get_json()
    drop = client.post(
        "/equipment", json={"name": "DropMe", "category": "MISC", "total_units": 1}
    ).get_json()
 
    client.delete(f"/equipment/{drop['id']}")
 
    response = client.get("/equipment")
    assert response.get_json() == [keep]
 

#------------------------------------------------------------
# Checkout equipment
# ------------------------------------------------------------
def test_checkout_returns_rental_with_expected_fields(client):
    """Checking out equipment returns 201 and a rental linked to the item and renter."""
    payload = {"name": "Tent", "category": "Camping", "total_units": 2}
    equipment_id = client.post("/equipment", json=payload).get_json()["id"]
 
    response = client.post("/rentals", json={"equipment_id": equipment_id, "renter_id": 1})
    assert response.status_code == 201
 
    rental = response.get_json()
    assert isinstance(rental["id"], int)
    assert rental["equipment_id"] == equipment_id
    assert rental["renter_id"] == 1 
    assert rental["rental_date"] == date.today().isoformat()
    assert rental["return_date"] is None
 
 
def test_checkout_sets_due_date_seven_days_out(client):
    """The due date is set automatically to seven days after checkout."""
    payload = {"name": "Tent", "category": "Camping", "total_units": 1}
    equipment_id = client.post("/equipment", json=payload).get_json()["id"]
 
    response = client.post("/rentals", json={"equipment_id": equipment_id, "renter_id": 1})
 
    expected_due = (date.today() + timedelta(days=7)).isoformat()
    assert response.get_json()["due_date"] == expected_due
 
 
def test_checkout_appears_in_rental_list(client):
    """the new rental shows up in the rentals list."""
    payload = {"name": "Tent", "category": "Camping", "total_units": 1}
    equipment_id = client.post("/equipment", json=payload).get_json()["id"]
 
    rental = client.post(
        "/rentals", json={"equipment_id": equipment_id, "renter_id": 1}
    ).get_json()
 
    response = client.get("/rentals")
    assert response.get_json() == [rental]
 
 
def test_checkout_decrements_available_units_in_equipment_list(client):
    """One checkout decrements available_units by one and leaves total_units as is."""
    payload = {"name": "Tent", "category": "Camping", "total_units": 3}
    equipment_id = client.post("/equipment", json=payload).get_json()["id"]
 
    client.post("/rentals", json={"equipment_id": equipment_id, "renter_id": 1})
 
    # Only one item exists, so it is the first entry in the list
    item = client.get("/equipment").get_json()[0]
    assert item["available_units"] == 2
    assert item["total_units"] == 3
 
 
def test_checkout_unknown_equipment_returns_404_and_creates_nothing(client):
    """Checking out an id that does not exist returns 404 and records no rental."""
    response = client.post("/rentals", json={"equipment_id": 999, "renter_id": 1})
    assert response.status_code == 404
 
    # The failed checkout must not leave a rental behind
    assert client.get("/rentals").get_json() == []
 
 
def test_checkout_beyond_available_stock_expected_fail(client):
    """
    EXPECTED FAILURE: a 1-unit item can be checked out twice
    This is because a stock check is missing from checkout_equipment().
    """
    payload = {"name": "Tent", "category": "Camping", "total_units": 1}
    equipment_id = client.post("/equipment", json=payload).get_json()["id"]
 
    first = client.post("/rentals", json={"equipment_id": equipment_id, "renter_id": 1})
    second = client.post("/rentals", json={"equipment_id": equipment_id, "renter_id": 2})
    assert first.status_code == 201  # the only unit is rented
    assert second.status_code == 400  # no unit left, so this must be refused
 
    item = client.get("/equipment").get_json()[0]
    assert item["available_units"] >= 0



# ------------------------------------------------------------
# Record equipment damage
# ------------------------------------------------------------
def test_new_equipment_has_no_damage_notes(client):
    """A newly added item has no damage recorded."""
    payload = {"name": "Tent", "category": "Camping", "total_units": 1}
    created = client.post("/equipment", json=payload).get_json()
    assert created["damage_notes"] is None

def test_record_damage_stores_description(client):
    """Recording damage returns 200 and the item with the description in damage_notes."""
    payload = {"name": "Tent", "category": "Camping", "total_units": 1}
    equipment_id = client.post("/equipment", json=payload).get_json()["id"]

    response = client.patch(
        f"/equipment/{equipment_id}/damage", json={"description": "broken zipper"}
    )
    assert response.status_code == 200
    item = response.get_json()
    assert item["id"] == equipment_id
    assert item["damage_notes"] == "broken zipper"
