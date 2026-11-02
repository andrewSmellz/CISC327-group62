# ============================================================
# TESTS FOR ANDREW'S FEATURES (Table B)
# ============================================================
# Features: add / list / view / update / delete equipment, mark equipment
# in or out of service, check availability, check out equipment, web UI.
# ============================================================




# ------------------------------------------------------------
# Add equipment 
# ------------------------------------------------------------
def test_add_equipment_returns_exepected(client):
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
    payload = {
        "name": "snow mobile", 
        "category": "winter",
        "total_units": 2 
    }
    response1 = client.post("/equipment", json=payload)
    response2 = client.get(f"/equipment/{response1['id']}")
    assert response2.status_code == 200
    assert response2.get_json() == response1

def test_equipment_get_unique_id(client):
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
    """The equipment list is empty before anything has been added."""
    response = client.get("/equipment")
    assert response.status_code == 200
    assert response.get_json() == []
 
 
def test_added_equipment_appears_in_list(client):
    """Create-then-verify: the new item shows up in the equipment list unchanged."""
    payload = {"name": "Kayak", "category": "Water", "total_units": 2}
    created = client.post("/equipment", json=payload).get_json()
 
    response = client.get("/equipment")
    assert response.status_code == 200
    assert response.get_json() == [created]
 
 
def test_list_equipment_returns_all_items_in_order(client):
    """Three added items all appear in the list, in the order they were added."""
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
 
    # Verify the resulting state, not just the status code
    assert client.get("/equipment").get_json() == []
 
 
def test_delete_equipment_only_removes_target(client):
    """Deleting one item leaves the other item untouched."""
    keep = client.post(
        "/equipment", json={"name": "Keep", "category": "MISC", "total_units": 1}
    ).get_json()
    drop = client.post(
        "/equipment", json={"name": "Drop", "category": "MISC", "total_units": 1}
    ).get_json()
 
    client.delete(f"/equipment/{drop['id']}")
 
    response = client.get("/equipment")
    assert response.get_json() == [keep]
 
 
 