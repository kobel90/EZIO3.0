import tkinter as tk
from tkinter import ttk, messagebox
import csv
import pandas as pd
from datetime import datetime
import os
from zielkontrolle import ZielKontrolle
import json
import time
from datetime import datetime
from colorama import Fore, Style
import matplotlib.pyplot as plt

ZIELKONTROLLE = ZielKontrolle()
CSV_PATH = "guv_log.csv"
BOT_RUNNING_FLAG = True

class StatusPanel:
    def __init__(self, master):
        self.master = master
        master.title("EZIO STATUS")
        master.geometry("300x250")
        master.resizable(False, False)

        self.pnl_label = ttk.Label(master, text="PnL heute: ...")
        self.ziel_label = ttk.Label(master, text="Zielstatus: ...")
        self.progress = ttk.Progressbar(master, orient="horizontal", length=200, mode="determinate")
        self.time_label = ttk.Label(master, text="Letztes Update: ...")
        self.status_label = ttk.Label(master, text="Bot läuft")
        self.stop_button = ttk.Button(master, text="Bot stoppen", command=self.stop_bot)

        self.pnl_label.pack(pady=3)
        self.ziel_label.pack(pady=3)
        self.progress.pack(pady=3)
        self.time_label.pack(pady=3)
        self.status_label.pack(pady=3)
        self.stop_button.pack(pady=5)

        self.update_loop()

    def stop_bot(self):
        global BOT_RUNNING_FLAG
        BOT_RUNNING_FLAG = False
        self.status_label.config(text="Bot gestoppt")
        self.stop_button.config(state=tk.DISABLED)

    def get_heutiger_gewinn(self):
        try:
            heute = datetime.now().date()
            gewinn = 0.0
            with open(CSV_PATH, newline="") as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    zeitwert = row['Zeitpunkt']
                    if len(zeitwert.strip()) == 10:
                        zeitpunkt = datetime.strptime(zeitwert, '%Y-%m-%d').date()
                    else:
                        zeitpunkt = datetime.strptime(zeitwert, '%Y-%m-%d %H:%M:%S').date()
                    if zeitpunkt == heute:
                        gewinn += float(row['Balance'])
            return round(gewinn, 2)
        except Exception as e:
            return f"Fehler: {str(e)}"

    def update_loop(self):
        gewinn = self.get_heutiger_gewinn()

        if isinstance(gewinn, (int, float)):
            ziel_status = ZIELKONTROLLE.bewertung(gewinn)
            zielwert = ZIELKONTROLLE.heutiges_ziel() or 1
            fortschritt = min(100, max(0, int((gewinn / zielwert) * 100)))
            self.progress['value'] = fortschritt
        else:
            ziel_status = gewinn
            self.progress['value'] = 0

        jetzt = datetime.now().strftime('%H:%M:%S')
        self.pnl_label.config(text=f"📈 PnL heute: {gewinn} $")
        self.ziel_label.config(text=f"❤️ Zielstatus: {ziel_status}")
        self.time_label.config(text=f"🕓 Letztes Update: {jetzt}")
        self.status_label.config(text="Bot läuft" if BOT_RUNNING_FLAG else "Bot gestoppt")

        self.master.after(5000, self.update_loop)

    def zeige_dashboard(pfad: str = "status_panel.json", interval: int = 5):
        """
        Zeigt das Live-Dashboard im Terminal an (liest regelmäßig aus JSON-Datei).
        """
        while True:
            os.system("clear")  # Für Windows: "cls"
            print(f"{Fore.CYAN}=== EZIO LIVE-DASHBOARD ({datetime.now().strftime('%H:%M:%S')}) ==={Style.RESET_ALL}")

            try:
                with open(pfad, "r") as f:
                    daten = json.load(f)

                print(f"{Fore.YELLOW}Modus: {daten['modus']}{Style.RESET_ALL}")
                print(f"Kapital: {Fore.GREEN}{daten['equity']:.2f} CHF{Style.RESET_ALL}")
                print(f"Verfügbare Margin: {Fore.GREEN}{daten['margin']['verfuegbar']:.2f} CHF{Style.RESET_ALL}")
                print(f"Genutzte Margin: {Fore.RED}{daten['margin']['genutzt']:.2f} CHF{Style.RESET_ALL}")

                if "trades" in daten:
                    print(f"\n{Fore.YELLOW}Trades:{Style.RESET_ALL}")
                    print(f"Gewinn: {Fore.GREEN}{daten['trades']['gewinn']}{Style.RESET_ALL} | "
                          f"Verlust: {Fore.RED}{daten['trades']['verlust']}{Style.RESET_ALL} | "
                          f"Win-Rate: {Fore.MAGENTA}{daten['trades']['rate']}%{Style.RESET_ALL}")

                if "signale" in daten:
                    print(f"\n{Fore.CYAN}Letzte Signale:{Style.RESET_ALL}")
                    for s in daten["signale"]:
                        print(f"– {s['epic']}: {s['direction']} ({s['confidence']})")

            except Exception as e:
                print(f"{Fore.RED}Fehler beim Einlesen der Statusdatei: {e}{Style.RESET_ALL}")

            time.sleep(interval)


    def show_warning(title: str, message: str, level="warning"):
        root = tk.Tk()
        root.withdraw()

        if level == "warning":
            messagebox.showwarning(title, message)
        elif level == "info":
            messagebox.showinfo(title, message)
        elif level == "error":
            messagebox.showerror(title, message)

        root.destroy()

        try:
            df = pd.read_json("status_panel.json")  # oder dein korrekter Pfad
        except Exception as e:
            print(f"Fehler beim Laden der Dashboard-Datei: {e}")
            return

        if "Datum" in df.columns:
            df = df.sort_values("Datum")
        else:
            print("⚠️ Spalte 'Datum' fehlt – Datenstruktur prüfen.")

def starte_statuspanel():
    root = tk.Tk()
    panel = StatusPanel(root)
    root.mainloop()
