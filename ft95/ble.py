"""Client BLE pour le Beurer FT95 (scan, découverte GATT, écoute des mesures)."""
from __future__ import annotations

import asyncio
import sys
from typing import Callable, List, Optional

from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

from .decode import Measurement, decode_health_thermometer, decode_heuristic, make_measurement

HEALTH_THERMOMETER_SERVICE = "00001809-0000-1000-8000-00805f9b34fb"
TEMPERATURE_MEASUREMENT_CHAR = "00002a1c-0000-1000-8000-00805f9b34fb"

NAME_HINTS = ("ft95", "ft 95", "beurer")


def looks_like_ft95(name: Optional[str]) -> bool:
    if not name:
        return False
    low = name.lower()
    return any(h in low for h in NAME_HINTS)


async def scan(duration: float = 10.0) -> List[BLEDevice]:
    devices = await BleakScanner.discover(timeout=duration)
    return list(devices)


async def find_ft95(timeout: float = 15.0) -> Optional[BLEDevice]:
    """Cherche un appareil dont le nom ressemble au FT95 (ou qui expose le service thermomètre)."""

    def _filter(_: BLEDevice, adv: AdvertisementData) -> bool:
        if looks_like_ft95(adv.local_name):
            return True
        return HEALTH_THERMOMETER_SERVICE in (adv.service_uuids or [])

    return await BleakScanner.find_device_by_filter(_filter, timeout=timeout)


async def dump_gatt(address_or_device, out=print) -> None:
    """Liste tous les services/caractéristiques de l'appareil (aide au reverse-engineering)."""
    async with BleakClient(address_or_device) as client:
        out(f"Connecté : {client.is_connected}")
        for service in client.services:
            out(f"Service {service.uuid}  handle={service.handle}")
            for char in service.characteristics:
                props = ",".join(char.properties)
                out(f"  Char {char.uuid}  [{props}]  handle={char.handle}")
                for desc in char.descriptors:
                    out(f"    Desc {desc.uuid} handle={desc.handle}")


class FT95Watcher:
    """Se connecte au FT95 et pousse chaque mesure décodée via un callback."""

    def __init__(
        self,
        device_provider: Callable[[], "asyncio.Future | BLEDevice"],
        on_measurement: Callable[[Measurement], None],
        heuristic: bool = False,
        log_raw: Optional[Callable[[str, bytes], None]] = None,
    ):
        self.device_provider = device_provider
        self.on_measurement = on_measurement
        self.heuristic = heuristic
        self.log_raw = log_raw

    async def _handle(self, char_uuid: str, data: bytes) -> None:
        if self.log_raw:
            self.log_raw(char_uuid, data)
        temp: Optional[float] = None
        if char_uuid.lower() == TEMPERATURE_MEASUREMENT_CHAR:
            temp = decode_health_thermometer(data)
            source = "health-thermometer"
        if temp is None:
            temp = decode_heuristic(data)
            source = "heuristique"
        if temp is not None:
            self.on_measurement(make_measurement(temp, data, source))

    async def run_forever(self, out=print) -> None:
        device = await self.device_provider()
        if not device:
            out("FT95 introuvable.")
            return
        out(f"Connecté à {device.name} ({device.address})")
        async with BleakClient(device) as client:
            targets: List[str] = []
            for service in client.services:
                for char in service.characteristics:
                    props = char.properties
                    if "indicate" in props or "notify" in props:
                        targets.append(char.uuid)
            if not targets:
                out("Aucune caractéristique notifiable trouvée.")
                return
            out(f"Écoute de {len(targets)} caractéristique(s) : {', '.join(targets)}")
            for uuid in targets:
                await client.start_notify(uuid, lambda d, data, u=uuid: asyncio.ensure_future(self._handle(u, data)))
            while True:
                await asyncio.sleep(1)
