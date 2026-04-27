"""
generate_demo_data.py — produces randomised but realistic org data for PROWESS.
All values are editable in the frontend before submission.
"""
from __future__ import annotations
import random
from faker import Faker

fake = Faker()
Faker.seed(0)

GEO_CLUSTERS = ["North", "South", "East", "West", "Downtown"]

TEAM_NAMES = [
    "Platform Engineering", "Product", "Design", "Data Science",
    "Sales", "Customer Success", "DevOps", "Security", "Marketing", "Finance"
]


def random_preferred_days(n: int = None) -> list[int]:
    n = n or random.randint(1, 3)
    return sorted(random.sample(range(5), k=min(n, 5)))


def generate(
    n_employees: int = 20,
    n_groups: int = 4,
    max_seats: int = None,
    n_weeks: int = 2,
    seed: int = None,
) -> dict:
    if seed is not None:
        random.seed(seed)
        Faker.seed(seed)

    if max_seats is None:
        max_seats = max(5, int(n_employees * random.uniform(0.4, 0.65)))

    min_daily = max(1, int(max_seats * random.uniform(0.3, 0.55)))

    # Employees
    employees = []
    for i in range(n_employees):
        emp_id = f"emp_{i:03d}"
        min_od = random.randint(1, 2)
        max_od = random.randint(min_od + 1, 4)
        # vacation: roughly 0-2 days scattered across the scheduled weeks
        vac_days = sorted(random.sample(range(5 * n_weeks), k=random.randint(0, 2)))
        employees.append({
            "id": emp_id,
            "name": fake.name(),
            "geo_cluster": random.choice(GEO_CLUSTERS),
            "vacation_days": vac_days,
            "min_office_days_per_week": min_od,
            "max_office_days_per_week": max_od,
            "preferred_days": random_preferred_days(),
        })

    emp_ids = [e["id"] for e in employees]

    # Groups / teams
    n_groups = min(n_groups, len(TEAM_NAMES))
    team_names = random.sample(TEAM_NAMES, k=n_groups)
    groups = []

    # Shuffle employees and partition them into groups (allowing overlap)
    shuffled = emp_ids[:]
    random.shuffle(shuffled)
    base_size = max(3, n_employees // n_groups)

    for gi in range(n_groups):
        # Pick a core set
        start = (gi * base_size) % n_employees
        core = shuffled[start: start + base_size]
        # Allow up to 2 cross-group members for intersectionality
        extras = random.sample(
            [e for e in emp_ids if e not in core],
            k=min(2, n_employees - len(core))
        )
        members = list(dict.fromkeys(core + extras))  # deduplicate, preserve order

        # Subgroups: split members into 2 sub-teams to model closer working groups
        half = max(2, len(members) // 2)
        subgroups = [members[:half], members[half:]] if len(members) >= 4 else []

        groups.append({
            "id": f"grp_{gi:02d}",
            "name": team_names[gi],
            "members": members,
            "min_overlap_days_per_week": random.randint(1, 2),
            "subgroups": subgroups,
            "overlap_weight": round(random.uniform(0.7, 1.3), 2),
        })

    org = {
        "max_seats": max_seats,
        "min_daily_in_person": min_daily,
        "priority_employees": 0.30,
        "priority_groups": 0.55,
        "priority_niceties": 0.15,
        "weeks": n_weeks,
    }

    return {
        "org": org,
        "employees": employees,
        "groups": groups,
    }


if __name__ == "__main__":
    import json
    data = generate(n_employees=12, n_groups=3, n_weeks=1, seed=42)
    print(json.dumps(data, indent=2))
