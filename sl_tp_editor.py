import json
import tkinter as tk
from tkinter import ttk, messagebox

CONFIG_PATH = "sl_tp_config.json"

class SLTPEditor:
    def __init__(self, master):
        self.master = master
        master.title("SL/TP Konfiguration")

        self.config = self.load_config()

        self.asset_var = tk.StringVar()
        self.sl_var = tk.StringVar()
        self.tp_var = tk.StringVar()

        # === GUI Layout ===
        ttk.Label(master, text="Asset auswählen:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.asset_menu = ttk.Combobox(master, textvariable=self.asset_var, values=list(self.config.keys()))
        self.asset_menu.grid(row=0, column=1, padx=10, pady=10)
        self.asset_menu.bind("<<ComboboxSelected>>", self.asset_selected)

        ttk.Label(master, text="Stop-Loss (%):").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.sl_entry = ttk.Entry(master, textvariable=self.sl_var)
        self.sl_entry.grid(row=1, column=1, padx=10, pady=5)

        ttk.Label(master, text="Take-Profit (%):").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.tp_entry = ttk.Entry(master, textvariable=self.tp_var)
        self.tp_entry.grid(row=2, column=1, padx=10, pady=5)

        self.save_button = ttk.Button(master, text="💾 Speichern", command=self.save_config)
        self.save_button.grid(row=3, column=0, columnspan=2, pady=15)

    def load_config(self):
        try:
            with open(CONFIG_PATH, "r") as f:
                return json.load(f)
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Laden der Konfiguration:\n{e}")
            return {}

    def save_config(self):
        asset = self.asset_var.get()
        try:
            sl = float(self.sl_var.get())
            tp = float(self.tp_var.get())
            self.config[asset] = {
                "stop_loss_percent": sl,
                "take_profit_percent": tp
            }
            with open(CONFIG_PATH, "w") as f:
                json.dump(self.config, f, indent=4)
            messagebox.showinfo("Gespeichert", f"SL/TP für {asset} erfolgreich gespeichert!")
        except ValueError:
            messagebox.showerror("Fehler", "Bitte gültige Zahlen eingeben.")

    def asset_selected(self, event=None):
        asset = self.asset_var.get()
        params = self.config.get(asset, {"stop_loss_percent": "", "take_profit_percent": ""})
        self.sl_var.set(params.get("stop_loss_percent", ""))
        self.tp_var.set(params.get("take_profit_percent", ""))


# === Start direkt testen ===
if __name__ == "__main__":
    root = tk.Tk()
    app = SLTPEditor(root)
    root.mainloop()