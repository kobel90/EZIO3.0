import pandas as pd
import os
from trading_ki import TradingKI

def lade_testdaten(pfad="testdaten.csv"):
    if not os.path.exists(pfad):
        print(f"❌ Datei {pfad} wurde nicht gefunden.")
        return []

    try:
        df = pd.read_csv(pfad)

        if df.empty:
            print("⚠️ Die CSV-Datei ist leer.")
            return []

        benötigte_spalten = [
            "epic", "price", "volumen", "volumen_schnitt", "rsi", "macd", "signal",
            "ema50", "ema200", "support", "resistance", "fibonacci", "nachrichten"
        ]

        fehlende = [spalte for spalte in benötigte_spalten if spalte not in df.columns]
        if fehlende:
            print(f"❌ Fehlende Spalten in CSV: {fehlende}")
            return []

        daten = []
        for _, row in df.iterrows():
            try:
                fibonacci = [float(x.strip()) for x in str(row["fibonacci"]).split(",") if x.strip()]
                daten.append({
                    "epic": row["epic"],
                    "price": float(row["price"]),
                    "volumen": float(row["volumen"]),
                    "volumen_schnitt": float(row["volumen_schnitt"]),
                    "rsi": float(row["rsi"]),
                    "macd": float(row["macd"]),
                    "signal": float(row["signal"]),
                    "ema50": float(row["ema50"]),
                    "ema200": float(row["ema200"]),
                    "support": float(row["support"]),
                    "resistance": float(row["resistance"]),
                    "fibonacci": fibonacci,
                    "nachrichten": [str(row["nachrichten"])]
                })
            except Exception as row_err:
                print(f"⚠️ Fehler in Zeile: {row.to_dict()} → {row_err}")
                continue

        return daten

    except Exception as e:
        print(f"❌ Fehler beim Lesen der Datei {pfad}: {e}")
        return []

def simuliere_testlauf():
    ki = TradingKI()
    testdaten = lade_testdaten()

    for datensatz in testdaten:
        epic = datensatz["epic"]
        print(f"\n🧪 Test für: {epic}")
        signal = ki.analysiere_signal(datensatz)
        confidence = ki.bewerte_confidence(epic, datensatz)
        dauer = ki.schaetze_trade_dauer(datensatz)
        risiko = ki.risikobewertung(epic, confidence, ki.vola_ki.schaetze_volatilitaet(datensatz["preise"]))

        print(f"➡️ Signal: {signal}")
        print(f"📊 Confidence: {confidence}")
        print(f"⏱️ Geschätzte Dauer: {dauer} Min")
        print(f"⚖️ Risiko: {risiko}")
        ki.zeige_analysebericht(epic)

if __name__ == "__main__":
    simuliere_testlauf()