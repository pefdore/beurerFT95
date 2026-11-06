"""Un cycle FT95 : connexion, réception du lot, affichage de la valeur candidate.

Exécuté dans un sous-processus par ft95.watch/ft95.widget pour contourner le bug
bleak/WinRT sous Windows (état global de l'interpréteur corrompu après un cycle).
"""
import argparse
import asyncio
import json

from .ble import FT95Watcher, find_ft95


def main() -> int:
    parser = argparse.ArgumentParser(prog="ft95-onecycle")
    parser.add_argument("--address", help="Adresse MAC du FT95 (optionnelle).")
    parser.add_argument("--wait-first", type=float, default=20.0, help="Attente max (s) de la 1re valeur.")
    parser.add_argument("--collect", type=float, default=8.0, help="Durée (s) de réception du lot.")
    args = parser.parse_args()

    async def resolve():
        if args.address:
            from bleak import BleakScanner

            d = await BleakScanner.find_device_by_address(args.address, timeout=15.0)
            if not d:
                print("FT95 introuvable.")
                return None
            return d
        d = await find_ft95()
        if not d:
            print("FT95 introuvable.")
            return None
        return d

    def on_measurement(m) -> None:
        print(
            "FT95CAND "
            + json.dumps(
                {
                    "temperature_c": m.temperature_c,
                    "raw": m.raw,
                    "source": m.source,
                    "size": getattr(watcher, "last_batch_size", 0),
                }
            ),
            flush=True,
        )

    watcher = FT95Watcher(resolve, on_measurement)
    state = {"last_emitted": None, "seen_raws": set(), "prev_batch_size": 0}
    try:
        asyncio.run(watcher._one_cycle(print, args.wait_first, args.collect, state))
    except Exception as exc:
        print(f"Erreur cycle : {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
