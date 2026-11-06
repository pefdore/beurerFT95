"""Copie dans le presse-papiers sans dépendance externe (Tkinter)."""
from __future__ import annotations


def copy_text(text: str) -> bool:
    try:
        import tkinter

        root = tkinter.Tk()
        root.withdraw()
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update()
        root.destroy()
        return True
    except Exception:
        return False
