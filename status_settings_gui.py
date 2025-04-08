import tkinter as tk
from tkinter import ttk
import json
import os

SETTINGS_FILE = "status_panel_settings.json"

DEFAULT_SETTINGS = {
    "modus": "classic",
    "zielwert": 50.0,
    "risiko_modus": "NIEDRIG",
    "live_modus": False
}

class SettingsFenster:
    def __init__(self, master):
        self.master = master
        master.title("⚙️ EZIO Einstellungen")
        master.geometry("300x260")
        master.resizable(False, False)

        self.settings = self.lade_einstellungen()

        # Modus Auswahl
        ttk.Label(master, text="Strategie-Modus:").pack(pady=5)
        self.modus_var = tk.StringVar(value=self.settings["modus"])
        self.modus_combo = ttk.Combobox(master, textvariable=self.modus_var, values=["classic", "confidence", "news"])
        self.modus_combo.pack()

        # Zielwert
        ttk.Label(master, text="🎯 Tagesziel (CHF):").pack(pady=5)
        self.ziel_entry = ttk.Entry(master)
        self.ziel_entry.insert(0, str(self.settings["zielwert"]))
        self.ziel_entry.pack()

        # Risiko Modus
        ttk.Label(master, text="⚠️ Risikoprofil:").pack(pady=5)
        self.risiko_var = tk.StringVar(value=self.settings["risiko_modus"])
        self.risiko_combo = ttk.Combobox(master, textvariable=self.risiko_var, values=["NIEDRIG", "MITTEL", "HOCH"])
        self.risiko_combo.pack()

        # Live-Modus Toggle
        self.live_var = tk.BooleanVar(value=self.settings["live_modus"])
        self.live_check = ttk.Checkbutton(master, text="🔴 Live-Modus aktivieren", variable=self.live_var)
        self.live_check.pack(pady=5)

        self.back_button = ttk.Button(master, text="🔙 Zurück zum Menü", command=self.zurueck_zum_menue)
        self.back_button.pack(pady=8)

        # Speichern-Button
        ttk.Button(master, text="💾 Einstellungen speichern", command=self.speichern).pack(pady=10)

    def lade_einstellungen(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    return json.load(f)
            except:
                pass
        return DEFAULT_SETTINGS.copy()

    def speichern(self):
        try:
            neue_settings = {
                "modus": self.modus_var.get(),
                "zielwert": float(self.ziel_entry.get()),
                "risiko_modus": self.risiko_var.get(),
                "live_modus": self.live_var.get()
            }
            with open(SETTINGS_FILE, "w") as f:
                json.dump(neue_settings, f, indent=4)
            tk.messagebox.showinfo("Erfolg", "Einstellungen wurden gespeichert ✅")
        except Exception as e:
            tk.messagebox.showerror("Fehler", f"Speichern fehlgeschlagen: {e}")


def starte_settings_gui():
    root = tk.Tk()
    app = SettingsFenster(root)
    root.mainloop()

# Testlauf (nur direkt beim Ausführen)
if __name__ == "__main__":
    starte_settings_gui()
