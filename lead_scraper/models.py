from dataclasses import dataclass, asdict


@dataclass
class Lead:
    name: str
    org_type: str
    phone: str
    email: str
    address: str
    city: str
    state: str

    def to_dict(self) -> dict:
        row = asdict(self)
        row["Type"] = row.pop("org_type")
        row["Name"] = row.pop("name")
        row["Phone"] = row.pop("phone")
        row["Email"] = row.pop("email")
        row["Address"] = row.pop("address")
        row["City"] = row.pop("city")
        row["State"] = row.pop("state")
        return row
