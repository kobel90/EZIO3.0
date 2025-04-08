# guv_visualizer.py
import pandas as pd
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from datetime import datetime
import matplotlib.pyplot as plt

def zeige_guv_verlauf(csv_datei="guv_log.csv"):
    try:
        # 1. CSV einlesen (mit explizitem Header, falls vorhanden)
        df = pd.read_csv(
            csv_datei,
            sep=";",
            names=["Zeit", "Epic", "Gewinn", "Confidence", "Risiko", "Dauer"],
            skiprows=1  # falls erste Zeile ein Header ist
        )

        # 2. Zeitstempel sicher parsen
        df["Zeit"] = pd.to_datetime(df["Zeit"], format="%Y-%m-%d %H:%M:%S", errors="coerce")
        df = df.dropna(subset=["Zeit"])
        df = df.sort_values("Zeit")

        # 3. Prüfen auf leeren DataFrame
        if df.empty:
            print("Keine gültigen GUV-Daten zum Anzeigen vorhanden.")
            return

        # 4. Kumulierte GUV-Linie zeichnen
        df["Kumuliert"] = df["Gewinn"].cumsum()
        plt.figure(figsize=(10, 5))
        plt.plot(df["Zeit"], df["Kumuliert"], label="Kumulierte G/V", linewidth=2)
        plt.axhline(y=0, color="gray", linestyle="--")
        plt.xlabel("Zeit")
        plt.ylabel("CHF")
        plt.title("Gewinn-/Verlustverlauf")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.show()

        # 5. Heatmap: Tagesgewinne nach Woche & Wochentag
        df["Datum"] = df["Zeit"].dt.date
        df["Wochentag"] = df["Zeit"].dt.day_name()
        df["Woche"] = df["Zeit"].dt.isocalendar().week

        heatmap_data = df.groupby(["Woche", "Wochentag"])["Gewinn"].sum().unstack().fillna(0)

        if not heatmap_data.empty:
            plt.figure(figsize=(12, 6))
            sns.heatmap(heatmap_data, annot=True, fmt=".2f", cmap="RdYlGn", center=0)
            plt.title("Heatmap Tagesgewinne (nach Woche & Wochentag)")
            plt.xlabel("Wochentag")
            plt.ylabel("Woche")
            plt.tight_layout()
            plt.show()
        else:
            print("Keine Heatmap-Daten vorhanden (alle Gewinne = 0 oder leer).")

    except Exception as e:
        print(f"❌ Fehler beim Zeichnen des GUV-Verlaufs: {e}")

def lade_guv_daten(pfad: str = "guv_log.csv") -> pd.DataFrame:
    try:
        df = pd.read_csv(pfad, sep=";", names=["datum", "epic", "gewinn", "confidence", "risiko", "dauer"], skiprows=1)
        if "datum" in df.columns:
            df["datum"] = pd.to_datetime(df["datum"], errors="coerce")
            df = df.dropna(subset=["datum"])
            df = df.sort_values("datum")
            return df
        else:
            print("⚠️ Spalte 'datum' fehlt in guv_log.csv")
            return pd.DataFrame()
    except Exception as e:
        print(f"❌ Fehler beim Laden von G/V-Daten: {e}")
        return pd.DataFrame()

def zeige_gewinnverlauf():
    df = lade_guv_daten()
    if df.empty:
        print("⚠️ Keine Daten für Gewinnverlauf.")
        return

    plt.figure(figsize=(8, 4))
    plt.plot(df["datum"], df["gewinn"], marker="o", linestyle="-", color="blue")
    plt.title("Täglicher Gewinnverlauf")
    plt.xlabel("Datum")
    plt.ylabel("Gewinn (CHF)")
    plt.grid(True)
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    zeige_guv_verlauf()     # Zeigt Verlauf & Heatmap
    zeige_gewinnverlauf()   # Zeigt einfachen Tagesverlauf