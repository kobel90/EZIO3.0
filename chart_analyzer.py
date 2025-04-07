# Schritt 1: Chart-Signale mit Kursverlauf verknüpfen
# Ziel: Die KI soll Kursverläufe (z. B. 7-Tage-Chart) analysieren und daraus Infos für das Signal ableiten können

import pandas as pd
import numpy as np
from typing import List, Optional

class ChartAnalyzer:
    def __init__(self):
        pass

    def analysiere_chartverlauf(self, df: pd.DataFrame) -> dict:
        """
        Analysiert eine Preisreihe und extrahiert chartbasierte Merkmale.
        """
        if df is None or df.empty or "close" not in df.columns:
            print(f"❌ Chart-Analyse abgebrochen – 'close'-Spalte fehlt.")
            return {"trend": "unknown", "volatilitaet": 0, "spike": False}

        closes = df["close"]
        returns = closes.pct_change().dropna()

        trend = "seitwärts"
        if not closes.empty and closes.iloc[-1] > closes.iloc[0] * 1.02:
            trend = "aufwärts"
        elif closes.iloc[-1] < closes.iloc[0] * 0.98:
            trend = "abwärts"

        volatilitaet = np.std(returns)
        spike = any(abs(returns) > 0.1)

        return {
            "trend": trend,
            "volatilitaet": round(volatilitaet, 5),
            "spike": spike
        }

    def kombiniere_mit_signal(self, signal: dict, chartanalyse: dict) -> dict:
        """
        Kombiniert ein bestehendes Signal mit Chartanalyse-Infos
        """
        kombi = signal.copy()
        kombi.update({
            "chart_trend": chartanalyse.get("trend"),
            "chart_volatilitaet": chartanalyse.get("volatilitaet"),
            "chart_spike": chartanalyse.get("spike")
        })
        return kombi
