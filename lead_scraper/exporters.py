from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

import pandas as pd

from .models import Lead


OUTPUT_COLUMNS = ["Name", "Type", "Phone", "Email", "Address", "City", "State"]


def export_to_csv(leads: Iterable[Lead], output_path: str) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        for lead in leads:
            writer.writerow(lead.to_dict())


def export_to_excel(leads: Iterable[Lead], output_path: str) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [lead.to_dict() for lead in leads]
    df = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    df.to_excel(path, index=False)
