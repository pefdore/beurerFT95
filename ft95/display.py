"""Fenêtre d'affichage toujours visible (Tkinter, toujours au premier plan)."""
from __future__ import annotations

import tkinter as tk
from typing import Optional

from .decode import Measurement
from .storage import load_history


class DisplayWindow:
    def __init__(self, store=None, jsonl_path: Optional[str] = None):
        self.store = store
        self.jsonl_path = jsonl_path
        self.root = tk.Tk()
        self.root.title("Beurer FT95")
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#101418")
        self.root.geometry("420x320")

        self.temp_var = tk.StringVar(value="--.- °C")
        self.time_var = tk.StringVar(value="En attente d'une mesure…")
        self.hist_var = tk.StringVar(value="")

        tk.Label(
            self.root,
            textvariable=self.temp_var,
            font=("Segoe UI", 64, "bold"),
            fg="#ffffff",
            bg="#101418",
        ).pack(pady=(20, 5))
        tk.Label(
            self.root,
            textvariable=self.time_var,
            font=("Segoe UI", 11),
            fg="#8fa3b3",
            bg="#101418",
        ).pack()
        tk.Label(
            self.root,
            text="Historique",
            font=("Segoe UI", 10, "bold"),
            fg="#5c7086",
            bg="#101418",
        ).pack(pady=(15, 0))
        tk.Label(
            self.root,
            textvariable=self.hist_var,
            font=("Consolas", 11),
            fg="#c7d3de",
            bg="#101418",
            justify="left",
            anchor="w",
        ).pack(fill="both", expand=True, padx=20, pady=(0, 10))

        self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)

    def show(self, m: Measurement) -> None:
        self.temp_var.set(m.display())
        self.time_var.set(m.timestamp.strftime("%H:%M:%S") + "  •  copié dans le presse-papiers")
        self.refresh_history()

    def refresh_history(self) -> None:
        if not self.jsonl_path:
            return
        lines = [f"{m.timestamp.strftime('%H:%M:%S')}  {m.temperature_c:.1f} °C" for m in load_history(self.jsonl_path, 8)]
        self.hist_var.set("\n".join(reversed(lines)))

    def run(self) -> None:
        self.refresh_history()
        self.root.mainloop()
