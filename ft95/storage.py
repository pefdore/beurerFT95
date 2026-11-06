"""Persistance des mesures : CSV et JSON Lines."""
from __future__ import annotations

import csv
import json
import os
from typing import List

from .decode import Measurement

CSV_FIELDS = ["timestamp", "temperature_c", "source", "raw"]


class MeasurementStore:
    def __init__(self, csv_path: str, jsonl_path: str):
        self.csv_path = csv_path
        self.jsonl_path = jsonl_path

    def save(self, m: Measurement) -> None:
        self._append_csv(m)
        self._append_jsonl(m)

    def _append_csv(self, m: Measurement) -> None:
        new = not os.path.exists(self.csv_path)
        with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new:
                w.writerow(CSV_FIELDS)
            w.writerow([m.timestamp.isoformat(timespec="seconds"), f"{m.temperature_c:.1f}", m.source, m.raw])

    def _append_jsonl(self, m: Measurement) -> None:
        with open(self.jsonl_path, "a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "timestamp": m.timestamp.isoformat(timespec="seconds"),
                        "temperature_c": m.temperature_c,
                        "source": m.source,
                        "raw": m.raw,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

    def load_last(self) -> Measurement | None:
        try:
            with open(self.jsonl_path, "r", encoding="utf-8") as f:
                lines = [ln for ln in f if ln.strip()]
            if not lines:
                return None
            obj = json.loads(lines[-1])
            from datetime import datetime

            return Measurement(
                temperature_c=obj["temperature_c"],
                timestamp=datetime.fromisoformat(obj["timestamp"]),
                raw=obj.get("raw", ""),
                source=obj.get("source", ""),
            )
        except (OSError, ValueError, KeyError):
            return None


def load_history(jsonl_path: str, limit: int = 20) -> List[Measurement]:
    from datetime import datetime

    out: List[Measurement] = []
    try:
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for ln in f:
                if not ln.strip():
                    continue
                try:
                    obj = json.loads(ln)
                    out.append(
                        Measurement(
                            temperature_c=obj["temperature_c"],
                            timestamp=datetime.fromisoformat(obj["timestamp"]),
                            raw=obj.get("raw", ""),
                            source=obj.get("source", ""),
                        )
                    )
                except (ValueError, KeyError):
                    continue
    except OSError:
        return []
    return out[-limit:]
