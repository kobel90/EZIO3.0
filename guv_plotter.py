import pandas as pd
import matplotlib.pyplot as plt

# CSV-Dateien einlesen
ziel_df = pd.read_csv("zielplan.csv")
guv_df = pd.read_csv("guv_log.csv")

# Datumsfelder in echte Datumstypen umwandeln
ziel_df["Datum"] = pd.to_datetime(ziel_df["Datum"])
guv_df["Zeitpunkt"] = pd.to_datetime(guv_df["Zeitpunkt"])

# Diagramm erstellen
plt.figure(figsize=(10, 5))
plt.plot(ziel_df["Datum"], ziel_df["Zielbetrag"], label="📈 Zielbetrag", linewidth=2)
plt.plot(guv_df["Zeitpunkt"], guv_df["Balance"], label="📉 Realer Gewinn", linewidth=2)

# Formatierungen
plt.title("Zielplan vs. echte Performance")
plt.xlabel("Datum")
plt.ylabel("Betrag in CHF")
plt.legend()
plt.grid(True)

# Anzeige in Konsole (ohne extra Fenster)
plt.tight_layout()
plt.show()