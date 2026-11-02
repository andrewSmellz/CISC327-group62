class Equipment:
    def __init__(self, id, name, category, total_units, available_units, is_available=True,damage_notes=None):
        self.id = id
        self.name = name
        self.category = category
        self.total_units = total_units
        self.available_units = available_units
        self.is_available = is_available  # False when out-of-service / under repair
        self.damage_notes = damage_notes  # None when no issues, otherwise contains a note

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "total_units": self.total_units,
            "available_units": self.available_units,
            "is_available": self.is_available,
            "damage_notes": self.damage_notes,
        }
