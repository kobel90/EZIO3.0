# utils/price_source_manager.py

import requests
import json
import time
import yfinance as yf
from utils.config_loader import load_config
from typing import Optional, List
import pandas as pd
from utils.epic_mapper import lade_epic_mapping
from utils.time_helper import get_best_period_interval
import numpy as np
from datetime import datetime, timedelta

class PriceSourceManager:
    def __init__(self):
        self.config = load_config()
        self.mapping = lade_epic_mapping()

    def get_price_yfinance(self, epic: str) -> Optional[float]:
        try:
            symbol = self.mapping[epic]["yfinance"]
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="1d", interval="1m")
            if data is not None and not data.empty:
                return float(data["Close"].iloc[-1])
            else:
                print(f"⚠️ Keine Daten bei yfinance für {symbol} (Epic: {epic})")
                return None
        except Exception as e:
            print(f"❌ Fehler bei yfinance Preisabruf für {epic}: {e}")
            return None

    def get_combined_price(self, epic: str) -> Optional[float]:
        price = self.get_price_yfinance(epic)
        if price is not None:
            print(f"✅ Preis via yfinance für {epic}: {price}")
            return price

        print(f"⛔ Kein Preis ermittelbar für {epic} über yfinance.")
        return None

    def log_price_source_score(self, source: str, epic: str, price: float, average: float):
        if not hasattr(self, "source_scores"):
            self.source_scores = {}
        if source not in self.source_scores:
            self.source_scores[source] = []
        abweichung = abs(price - average)
        self.source_scores[source].append(abweichung)
        letzte = self.source_scores[source][-10:]
        mean_deviation = sum(letzte) / len(letzte)
        print(f"📊 Quelle: {source} | Abweichung: {abweichung:.4f} | Ø (letzte 10): {mean_deviation:.4f}")

    def get_price_series_finnhub(self, epic: str, days: int = 30) -> Optional[pd.DataFrame]:
        print(f"🟦 [Start] Preisreihe von Finnhub anfordern für {epic} ({days} Tage)")

        try:
            symbol = self.get_symbol(epic, "finnhub")
            print(f"🟨 Symbol für Finnhub: {symbol}")

            resolution = self.get_finnhub_resolution(days)
            print(f"🟨 Verwendete Auflösung: {resolution}")

            end_time = int(time.time())
            start_time = int((datetime.now() - timedelta(days=days)).timestamp())

            url = "https://finnhub.io/api/v1/stock/candle"
            params = {
                "symbol": symbol,
                "resolution": resolution,
                "from": start_time,
                "to": end_time,
                "token": self.api_key
            }

            print(f"📤 Sende Anfrage an Finnhub: {url} mit Params: {params}")
            response = requests.get(url, params=params)
            print(f"📥 Antwortstatus: {response.status_code}")

            if response.status_code == 429:
                self.block_quota("finnhub", cooldown_minutes=10)
                print(f"⛔ Finnhub API-Limit erreicht (429) für {epic}")
                return None

            if response.status_code == 200:
                data = response.json()
                print(f"📦 Antwortdaten: {data if len(str(data)) < 500 else '[...gekürzt...]'}")

                if data.get("s") != "ok":
                    print(f"⚠️ Finnhub: Keine gültigen Daten für {symbol} ({epic}) – Status: {data.get('s')}")
                    return None

                if not data.get("t") or not data.get("c"):
                    print(f"❌ Leere 't' oder 'c'-Arrays in Rückgabe – Daten: {data}")
                    return None

                df = pd.DataFrame({
                    "timestamp": pd.to_datetime(data["t"], unit="s"),
                    "close": data["c"]
                })
                df.set_index("timestamp", inplace=True)

                print(f"✅ Finnhub-Zeitreihe erfolgreich erstellt für {epic} – {len(df)} Zeilen")
                return df[["close"]]
            else:
                print(f"❌ Fehlercode {response.status_code} bei Finnhub-Abfrage für {epic}")
        except Exception as e:
            print(f"❌ Ausnahme bei Finnhub-Zeitreihe für {epic}: {e}")
        return None

    def get_price_series_yfinance(self, epic: str, days: int = 30, interval: str = "1d") -> Optional[pd.DataFrame]:
        try:
            symbol = self.mapping[epic]["yfinance"]
            ticker = yf.Ticker(symbol)
            period, interval = get_best_period_interval(days)
            data = ticker.history(period=period, interval=interval)
            if data is not None and not data.empty and "Close" in data.columns:
                data = data.rename(columns={"Close": "close"})
                return data[["close"]]
            else:
                print(f"⚠️ Keine gültigen historischen Daten für {symbol} ({epic})")
                return None
        except Exception as e:
            print(f"❌ Fehler bei yfinance Preisreihe für {epic}: {e}")
            return None

    def get_combined_price_series(self, epic: str, days: int = 30) -> Optional[pd.Series]:
        series_finnhub = self.get_price_series_finnhub(epic, days)
        series_yf = self.get_price_series_yfinance(epic, days)

        valid_series = []
        for source_name, s in [("Finnhub", series_finnhub), ("YF", series_yf)]:
            if isinstance(s, pd.DataFrame):
                if "close" in s.columns and not s["close"].empty:
                    valid_series.append(s["close"])
                else:
                    print(f"⚠️ '{source_name}' → DataFrame aber keine gültige 'close'-Spalte oder leer. Epic: {epic}")
            else:
                print(f"⚠️ '{source_name}' → Ungültiger Typ: {type(s)} (Epic: {epic})")

        if not valid_series:
            print(f"❌ Keine gültigen Preisreihen vorhanden für Epic: {epic}")
            return None

        combined = pd.concat(valid_series, axis=1).mean(axis=1)
        return combined

    def get_symbol(self, epic: str, quelle: str) -> str:
        eintrag = self.mapping.get(epic)
        if not eintrag:
            print(f"⚠️ Kein Mapping gefunden für: {epic}")
            return epic
        symbol = eintrag.get(quelle)
        if not symbol:
            print(f"⚠️ Kein {quelle}-Symbol für: {epic}")
            return epic
        return symbol

    def get_finnhub_resolution(self, days: int) -> str:
        if days <= 5:
            return "5"
        elif days <= 10:
            return "15"
        elif days <= 30:
            return "30"
        elif days <= 90:
            return "60"
        else:
            return "D"

    def get_best_price_series(self, epic: str, days: int = 30) -> Optional[pd.DataFrame]:
        try:
            df = self.get_price_series_yfinance(epic, days=days)
            if df is not None and not df.empty:
                print(f"✅ Preisreihe via yfinance geladen für {epic} (Zeilen: {len(df)})")
                return df
            print(f"⚠️ Fallback auf Finnhub für {epic}")
            df_fallback = self.get_price_series_finnhub(epic, days=days)
            if df_fallback is not None and not df_fallback.empty:
                print(f"✅ Preisreihe via Finnhub geladen für {epic} (Zeilen: {len(df_fallback)})")
                return df_fallback
            raise ValueError("Keine gültige Preisreihe gefunden.")
        except Exception as e:
            print(f"❌ Fehler beim Laden der Preisreihe für {epic}: {e}")
            return None
