"""CLI ft95 : scan, découverte GATT, espion des trames, affichage temps réel, saisie manuelle."""
from __future__ import annotations

import argparse
import asyncio
import os
import queue
import sys
import threading
from pathlib import Path

from . import __version__
from .ble import FT95Watcher, dump_gatt, find_ft95, looks_like_ft95, scan
from .clipboard import copy_text
from .decode import Measurement, make_measurement
from .storage import MeasurementStore, load_history

DATA_DIR = Path(os.environ.get("FT95_DATA_DIR", Path.home() / ".ft95"))
CSV_PATH = DATA_DIR / "mesures.csv"
JSONL_PATH = DATA_DIR / "mesures.jsonl"


def get_store() -> MeasurementStore:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return MeasurementStore(str(CSV_PATH), str(JSONL_PATH))


def cmd_scan(args: argparse.Namespace) -> int:
    print(f"Scan BLE pendant {args.duration}s…")
    devices = asyncio.run(scan(args.duration))
    for d in sorted(devices, key=lambda x: (x.name or "").lower()):
        marker = "  <-- probable FT95" if looks_like_ft95(d.name) else ""
        print(f"{d.address}  {d.name or '(sans nom)'}{marker}")
    return 0


def cmd_gatt(args: argparse.Namespace) -> int:
    asyncio.run(dump_gatt(args.address))
    return 0


def cmd_pair(args: argparse.Namespace) -> int:
    async def run() -> None:
        from bleak import BleakScanner

        if args.address:
            device = await BleakScanner.find_device_by_address(args.address, timeout=15.0)
        else:
            device = await find_ft95()
        if not device:
            print("FT95 introuvable. Allumez-le (ou prenez une mesure) et relancez, ou essayez 'ft95 scan'.")
            return
        print(f"Connexion à {device.name} ({device.address})…")
        from bleak import BleakClient

        async with BleakClient(device) as client:
            try:
                if await client.pair():
                    print("Jumelage réussi. Vous pouvez lancer 'ft95 watch'.")
                else:
                    print("Jumelage refusé par l'appareil.")
            except Exception as exc:
                print(f"Échec du jumelage : {exc}")

    asyncio.run(run())
    return 0


def cmd_spy(args: argparse.Namespace) -> int:
    async def run() -> None:
        device = await find_ft95()
        if not device:
            print("FT95 introuvable.")
            return
        print(f"Espion sur {device.name} ({device.address}) — prenez une mesure puis Ctrl+C pour arrêter.")

        def log_raw(char_uuid: str, data: bytes) -> None:
            print(f"[{char_uuid}] {data.hex(' ')}")

        watcher = FT95Watcher(lambda: asyncio.sleep(0, result=device), lambda m: None, heuristic=False, log_raw=log_raw)
        await watcher.run_forever()

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass
    return 0


def cmd_watch(args: argparse.Namespace) -> int:
    store = get_store()
    address = getattr(args, "address_opt", None) or getattr(args, "address_pos", None)

    def pick_device():
        return find_ft95()

    async def resolve_device():
        if address:
            from bleak import BleakScanner

            d = await BleakScanner.find_device_by_address(address, timeout=15.0)
            if not d:
                raise SystemExit(f"Aucun appareil à l'adresse {address}. Lancez 'ft95 scan'.")
            return d
        d = await find_ft95()
        if not d:
            raise SystemExit("FT95 introuvable. Lancez 'ft95 scan' pour identifier son nom/adresse.")
        return d

    if args.no_gui:
        def on_measurement(m: Measurement) -> None:
            store.save(m)
            copy_text(f"{m.temperature_c:.1f}")
            print(f"Mesure : {m.display()} à {m.timestamp.strftime('%H:%M:%S')} — copiée dans le presse-papiers")

        watcher = FT95Watcher(resolve_device, on_measurement)
        try:
            asyncio.run(watcher.run_forever())
        except KeyboardInterrupt:
            pass
        return 0

    from .display import DisplayWindow

    win = DisplayWindow(store=store, jsonl_path=str(JSONL_PATH))
    q: "queue.Queue[Measurement]" = queue.Queue()

    def ble_thread() -> None:
        async def run() -> None:
            def on_measurement(m: Measurement) -> None:
                q.put(m)

            watcher = FT95Watcher(resolve_device, on_measurement)
            await watcher.run_forever()

        try:
            asyncio.run(run())
        except Exception as exc:
            print(f"BLE arrêté : {exc}", file=sys.stderr)

    threading.Thread(target=ble_thread, daemon=True).start()

    def poll() -> None:
        try:
            while True:
                m = q.get_nowait()
                store.save(m)
                copy_text(f"{m.temperature_c:.1f}")
                win.show(m)
        except queue.Empty:
            pass
        win.root.after(250, poll)

    win.root.after(250, poll)
    win.root.mainloop()
    return 0


def _run_ble(on_measurement, address=None, out=print) -> None:
    async def resolve_device():
        if address:
            from bleak import BleakScanner

            d = await BleakScanner.find_device_by_address(address, timeout=15.0)
            if not d:
                raise SystemExit(f"Aucun appareil à l'adresse {address}. Lancez 'ft95 scan'.")
            return d
        d = await find_ft95()
        if not d:
            raise SystemExit("FT95 introuvable. Allumez-le (ou prenez une mesure) et relancez, ou 'ft95 scan'.")
        return d

    watcher = FT95Watcher(resolve_device, on_measurement)
    try:
        asyncio.run(watcher.run_forever(out=out))
    except Exception as exc:
        print(f"BLE arrêté : {exc}", file=sys.stderr)


def cmd_widget(args: argparse.Namespace) -> int:
    from .widget import run_widget

    store = get_store()

    def ble_target(q):
        def on_measurement(m):
            store.save(m)
            copy_text(f"{m.temperature_c:.1f}")
            q.put(f"{m.temperature_c:.1f}")

        _run_ble(on_measurement, address=args.address)

    run_widget(ble_target)
    return 0


def cmd_manual(args: argparse.Namespace) -> int:
    store = get_store()
    m = make_measurement(args.temperature, b"", "saisie-manuelle")
    store.save(m)
    copy_text(f"{m.temperature_c:.1f}")
    print(f"Enregistré : {m.display()} — copié dans le presse-papiers.")
    return 0


def cmd_last(args: argparse.Namespace) -> int:
    ms = load_history(str(JSONL_PATH), limit=args.count)
    if not ms:
        print("Aucune mesure enregistrée.")
        return 1
    for m in reversed(ms):
        print(f"{m.timestamp.isoformat(timespec='seconds')}  {m.temperature_c:.1f} °C  ({m.source})")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="ft95",
        description="Affiche les températures du thermomètre Beurer FT95 sur votre PC.",
    )
    parser.add_argument("--version", action="version", version=f"ft95 {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("scan", help="Liste les appareils BLE à portée (10s par défaut).")
    p.add_argument("--duration", type=float, default=10.0)
    p.set_defaults(func=cmd_scan)

    p = sub.add_parser("gatt", help="Liste les services/caractéristiques d'un appareil.")
    p.add_argument("address")
    p.set_defaults(func=cmd_gatt)

    p = sub.add_parser("pair", help="Jumelle le FT95 (équivaut à l'ajout d'appareil Windows).")
    p.add_argument("address", nargs="?", help="Adresse MAC du FT95 (optionnelle).")
    p.set_defaults(func=cmd_pair)

    p = sub.add_parser("spy", help="Affiche les trames brutes du FT95 (reverse-engineering).")
    p.set_defaults(func=cmd_spy)

    p = sub.add_parser("watch", help="Écoute le FT95 et affiche les mesures (fenêtre + presse-papiers).")
    p.add_argument("address_pos", nargs="?", help="Adresse MAC du FT95 (optionnelle, positionnelle ou via --address).")
    p.add_argument("--address", dest="address_opt", help="Adresse MAC du FT95 (si le nom n'est pas détecté).")
    p.add_argument("--no-gui", action="store_true", help="Affichage en console uniquement.")
    p.set_defaults(func=cmd_watch)

    p = sub.add_parser("widget", help="Widget rond bleu (style miscale) : dernière température au premier plan.")
    p.add_argument("address", nargs="?", help="Adresse MAC du FT95 (optionnelle).")
    p.set_defaults(func=cmd_widget)

    p = sub.add_parser("manual", help="Enregistre une température saisie à la main (ex: 38.2).")
    p.add_argument("temperature", type=float)
    p.set_defaults(func=cmd_manual)

    p = sub.add_parser("last", help="Affiche les dernières mesures enregistrées.")
    p.add_argument("--count", type=int, default=10)
    p.set_defaults(func=cmd_last)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
