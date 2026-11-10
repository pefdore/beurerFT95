"""Permet `python -m ft95 <commande>` (et `pythonw -m ft95 widget` sans console)."""
from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
