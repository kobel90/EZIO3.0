import json
import os
import tkinter as tk
from tkinter import ttk
from datetime import datetime
import threading

LOGDATEI = "quellen_log.json"
UPDATE_INTERVAL_MS = 10000  # alle 10 Sekunden


def lade_quellen_logs(datei=LOGDATEI):
    if not os.path.exists(datei):
        return []
    try:
        with open(datei, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Fehler beim Lesen von {datei}: {e}")
        return []


def gruppiere_letzten_status(logs):
    status_dict = {}
    for eintrag in reversed(logs):
        quelle = eintrag.get("quelle")
        if quelle not in status_dict:
            status_dict[quelle] = eintrag
    return status_dict


class QuellenDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("📡 Live-Quellenstatus")
        self.tree = ttk.Treeview(root, columns=("Quelle", "Status", "Score", "Zeit"), show="headings")
        self.tree.heading("Quelle", text="Quelle")
        self.tree.heading("Status", text="Status")
        self.tree.heading("Score", text="Score")
        self.tree.heading("Zeit", text="Letzte Prüfung")

        self.tree.pack(fill="both", expand=True)

        # Farben pro Status
        self.status_farben = {
            "aktiv": "#a6e22e",
            "inaktiv": "#f92672",
            "fehler": "#f92672",
            "unbekannt": "#75715e"
        }

        self.aktualisiere_daten()

    def aktualisiere_daten(self):
        logs = lade_quellen_logs()
        letzter_status = gruppiere_letzten_status(logs)

        for i in self.tree.get_children():
            self.tree.delete(i)

        for quelle, eintrag in letzter_status.items():
            status = eintrag.get("status", "unbekannt")
            farbe = self.status_farben.get(status, "#ffffff")
            self.tree.insert("", "end", values=(
                eintrag.get("quelle"),
                status,
                eintrag.get("score"),
                eintrag.get("zeit")[-8:]  # nur Uhrzeit
            ), tags=(status,))
            self.tree.tag_configure(status, background=farbe)

        self.root.after(UPDATE_INTERVAL_MS, self.aktualisiere_daten)


if __name__ == "__main__":
    root = tk.Tk()
    app = QuellenDashboard(root)
    root.mainloop()