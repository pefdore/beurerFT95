"""Décodage des mesures de température (IEEE-11073 32-bit float et formats simples)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Measurement:
    temperature_c: float
    timestamp: datetime
    raw: str
    source: str

    def display(self) -> str:
        return f"{self.temperature_c:.1f} °C"


def decode_ieee11073_32bit(data: bytes) -> Optional[float]:
    """Décode un float 32 bits IEEE-11073 (mantisse uint24 + exposant int8)."""
    if len(data) < 4:
        return None
    mantissa = int.from_bytes(data[0:3], "little")
    exponent = int.from_bytes(data[3:4], "little", signed=True)
    return mantissa * (10 ** exponent)


def decode_health_thermometer(data: bytes) -> Optional[float]:
    """Décode une indication/notification 'Temperature Measurement' (0x2A1C).

    Format: flags (1 octet) puis température.
    - flags bit0 = 0 : unité Celsius, format IEEE-11073 32 bits
    - flags bit0 = 1 : unité Fahrenheit, mantisse uint16 + exposant int8
    """
    if len(data) < 4:
        return None
    flags = data[0]
    if flags & 0x01:
        mantissa = int.from_bytes(data[1:3], "little")
        exponent = int.from_bytes(data[3:4], "little", signed=True)
        value_f = mantissa * (10 ** exponent)
        return (value_f - 32.0) * 5.0 / 9.0
    if len(data) < 5:
        return None
    return decode_ieee11073_32bit(data[1:5])


def extract_timestamp(data: bytes) -> Optional[datetime]:
    """Extrait l'horodatage optionnel d'une trame 0x2A1C (flags bit1)."""
    if len(data) < 12 or not (data[0] & 0x02):
        return None
    year = int.from_bytes(data[5:7], "little")
    if year == 0:
        return None
    try:
        return datetime(
            year,
            data[7],
            data[8],
            data[9],
            data[10],
            data[11],
        )
    except ValueError:
        return None


def decode_heuristic(data: bytes) -> Optional[float]:
    """Cherche une température plausible encodée en little-endian (x100 ou x10).

    Utilisé en mode espion pour deviner le format des trames inconnues.
    Plage plausible : 30.0 - 45.0 °C.
    """
    for scale in (100.0, 10.0):
        for i in range(len(data) - 1):
            v = int.from_bytes(data[i : i + 2], "little") / scale
            if 30.0 <= v <= 45.0:
                return v
    return None


def make_measurement(temperature_c: float, raw: bytes, source: str) -> Measurement:
    return Measurement(
        temperature_c=round(temperature_c, 1),
        timestamp=datetime.now(),
        raw=raw.hex(),
        source=source,
    )
