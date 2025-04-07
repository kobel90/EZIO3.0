import pandas as pd
import os
from plyer import notification
import tkinter as tk
from tkinter import messagebox
from datetime import datetime, date

def show_warning(title: str, message: str, level="warning"):
    root = tk.Tk()
    root.withdraw()  # Versteckt das Hauptfenster

    if level == "warning":
        messagebox.showwarning(title, message)
    elif level == "info":
        messagebox.showinfo(title, message)
    elif level == "error":
        messagebox.showerror(title, message)

    root.destroy()

class ZielKontrolle:
    def __init__(self, pfad_zur_csv: str = "zielplan.csv"):
        self.ziel_csv = pfad_zur_csv
        self.zielplan = self.lade_zielplan()

    def lade_zielplan(self) -> pd.DataFrame:
        """Lädt die CSV-Datei und wandelt das Datum in datetime-Objekte um."""
        if not os.path.exists(self.ziel_csv):
            print("⚠️ Zielplan-Datei nicht gefunden:", self.ziel_csv)
            return pd.DataFrame()
        df = pd.read_csv(self.ziel_csv)  # oder explizit: sep=","
        df["Datum"] = pd.to_datetime(df["Datum"], dayfirst=True).dt.date
        return df

    def heutiges_ziel(self) -> float:
        """Gibt das Tagesziel für das heutige Datum zurück."""
        heute = date.today()
        zeile = self.zielplan[self.zielplan["Datum"] == heute]
        if not zeile.empty:
            return float(zeile.iloc[0]["Zielbetrag"])
        print(f"⚠️ Kein Zielwert für {heute} gefunden.")
        return None

    def bewertung(self, heutiger_gewinn: float) -> str:
        """Bewertet das Tagesergebnis und gibt eine passende Rückmeldung."""
        ziel = self.heutiges_ziel()
        if ziel is None:
            return "⚠️ Kein Tagesziel vorhanden"

        if heutiger_gewinn >= ziel * 1.05:
            show_warning("🥇 Ziel übertroffen!", f"{heutiger_gewinn:.2f} CHF – weiter so!", level="info")
            return "🔵 Ziel übertroffen"

        elif heutiger_gewinn >= ziel:
            show_warning("✅ Ziel erreicht", f"{heutiger_gewinn:.2f} CHF – super!", level="info")
            return "🟢 Ziel erreicht"

        elif heutiger_gewinn >= -ziel:
            return "🟡 Ziel noch nicht erreicht"

        else:
            show_warning("❌ Verlustgrenze erreicht", f"{heutiger_gewinn:.2f} CHF – Bot sollte gestoppt werden!", level="error")
            return "🔴 Verlustgrenze erreicht – Bot stoppen"

# Direkt-Test
if __name__ == "__main__":
    kontrolle = ZielKontrolle("zielplan.csv")
    guv = 5.80  # Beispielwert
    print("📅 Heutiges Ziel:", kontrolle.heutiges_ziel())
    print("📊 Status:", kontrolle.bewertung(guv))