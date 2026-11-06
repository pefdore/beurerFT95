"""Client BLE pour le Beurer FT95 (scan, découverte GATT, écoute des mesures)."""
from __future__ import annotations

import asyncio
import sys
from typing import Callable, List, Optional

from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

from .decode import Measurement, decode_health_thermometer, decode_heuristic, extract_timestamp, make_measurement

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
        self.batching = False
        self.batch: List[Measurement] = []
        self._first_item: Optional[asyncio.Event] = None

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
            m = make_measurement(temp, data, source)
            if self.batching:
                ts = extract_timestamp(data)
                if ts:
                    m.device_time = ts
                self.batch.append(m)
                if self._first_item:
                    self._first_item.set()
            else:
                self.on_measurement(m)

    async def run_forever(self, out=print, wait_after_emit: float = 10.0) -> None:
        """Boucle : se connecte, collecte le lot envoyé par le FT95, n'affiche que la
        mesure la plus récente, se déconnecte, puis attend la mesure suivante.

        Le FT95 ne peut pas mesurer pendant qu'il est connecté : il faut donc rester
        connecté le moins longtemps possible et ignorer les lots déjà traités.
        """
        last_emitted: Optional[Measurement] = None
        seen_raws: set = set()
        while True:
            device = await self.device_provider()
            if not device:
                out("FT95 introuvable, nouvelle tentative dans 5s…")
                await asyncio.sleep(5)
                continue
            out(f"Connecté à {device.name} ({device.address}) — réception du lot…")
            received = asyncio.Event()
            self._first_item = received
            self.batching = True
            self.batch = []
            try:
                async with BleakClient(device, disconnected_callback=lambda c: received.set()) as client:
                    targets: List[str] = []
                    for service in client.services:
                        for char in service.characteristics:
                            props = char.properties
                            if char.uuid.lower() == "00002a05-0000-1000-8000-00805f9b34fb":
                                continue
                            if "indicate" in props or "notify" in props:
                                targets.append(char.uuid)
                    active = 0
                    for uuid in targets:
                        try:
                            await client.start_notify(uuid, lambda d, data, u=uuid: asyncio.ensure_future(self._handle(u, data)))
                            active += 1
                        except Exception as exc:
                            out(f"Écoute impossible sur {uuid} : {exc}")
                    if active == 0:
                        out("Aucune écoute possible : réessayez, ou jumelez le FT95 dans les paramètres Bluetooth.")
                        await asyncio.sleep(5)
                        continue
                    try:
                        await asyncio.wait_for(received.wait(), timeout=15)
                        deadline = asyncio.get_event_loop().time() + 8.0
                        while asyncio.get_event_loop().time() < deadline:
                            n = len(self.batch)
                            await asyncio.sleep(2)
                            if len(self.batch) == n:
                                break
                        stamped = [m for m in self.batch if m.device_time is not None]
                        if stamped:
                            last = max(stamped, key=lambda m: m.device_time)
                            is_new = last_emitted is None or last.raw not in seen_raws
                        else:
                            unseen = [m for m in self.batch if m.raw not in seen_raws]
                            last = unseen[0] if unseen else None
                            is_new = last is not None
                        seen_raws.update(m.raw for m in self.batch)
                        out(f"Lot reçu : {len(self.batch)} valeur(s).")
                        if last and is_new:
                            last_emitted = last
                            self.on_measurement(last)
                            out(f"Nouvelle mesure : {last.display()} — copiée dans le presse-papiers.")
                        elif last:
                            out("Lot déjà traité — pas de nouvelle mesure.")
                        elif self.batch:
                            out("Lot déjà traité — pas de nouvelle mesure.")
                    except asyncio.TimeoutError:
                        out("Aucune donnée reçue — déconnexion.")
            except Exception as exc:
                out(f"Connexion perdue ({exc}) — nouvelle tentative dans 5s…")
            finally:
                self._first_item = None
                self.batching = False
                self.batch = []
            out("Thermomètre libéré — vous pouvez prendre une nouvelle mesure.")
            await asyncio.sleep(wait_after_emit)
