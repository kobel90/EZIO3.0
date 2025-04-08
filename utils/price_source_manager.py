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
import numpy as np  # Wird auch benötigt!

from datetime import datetime, timedelta

class PriceSourceManager:
    def __init__(self):
        self.config = load_config()
        self.mapping = lade_epic_mapping()
        self.quota_blocked_until = {}

        self.finnhub_key = self.config.get("finnhub_api_key")
        self.api_key = load_config().get("finnhub_api_key", "")

    def is_quota_blocked(self, source: str) -> bool:
        """Prüft, ob die Datenquelle aktuell blockiert ist (z. B. wegen 429)"""
        unblock_time = self.quota_blocked_until.get(source)
        if unblock_time and datetime.now() < unblock_time:
            return True
        return False

    def block_quota(self, source: str, cooldown_minutes: int = 10):
        until = datetime.now() + timedelta(minutes=cooldown_minutes)
        self.quota_blocked_until[source] = until

        print(f"⏱️ {source} blockiert bis {until.strftime('%H:%M:%S')}")

        # In Logdatei schreiben
        try:
            with open("quota_log.csv", "a") as f:
                f.write(
                    f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')},{source},{until.strftime('%Y-%m-%d %H:%M:%S')}\n")
        except Exception as e:
            print(f"⚠️ Fehler beim Schreiben in quota_log.csv: {e}")


    def get_price_finnhub(self, epic: str) -> Optional[float]:
        try:
            if self.is_quota_blocked("finnhub"):
                print(f"⚠️ Finnhub-API ist temporär blockiert für {epic}.")
                return None

            symbol = self.mapping[epic]["finnhub"]
            url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={self.finnhub_key}"
            response = requests.get(url)

            if response.status_code == 429:
                self.block_quota("finnhub", cooldown_minutes=10)
                print(f"⛔ Finnhub API-Limit erreicht (429) für {epic}")
                return None

            if response.status_code == 200:
                data = response.json()
                if "c" in data and data["c"] is not None:
                    return float(data["c"])
                else:
                    print(f"⚠️ Kein gültiger Preis in Finnhub-Daten für {epic}: {data}")
            else:
                print(f"❌ Fehlercode {response.status_code} bei Finnhub-Abfrage für {epic}")
        except Exception as e:
            print(f"❌ Fehler bei Finnhub-Preisabruf für {epic}: {e}")
        return None

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
            if "404" in str(e):
                print(f"⛔ 404: yfinance-Symbol nicht gefunden – {epic}")
            else:
                print(f"❌ Fehler bei yfinance Preisabruf für {epic}: {e}")
            return None

    def get_combined_price(self, epic: str) -> Optional[float]:
        price = self.get_price_yfinance(epic)
        if price is not None:
            print(f"✅ Preis via yfinance für {epic}: {price}")
            return price

        price = self.get_price_finnhub(epic)
        if price is not None:
            print(f"✅ Preis via finnhub für {epic}: {price}")
            return price

        print(f"⛔ Kein Preis ermittelbar für {epic} über verfügbare Quellen.")
        return None

    # In price_source_manager.py
    def log_price_source_score(self, source: str, epic: str, price: float, average: float):
        """Berechnet und speichert die Abweichung vom Mittelwert für jede Quelle."""
        if not hasattr(self, "source_scores"):
            self.source_scores = {}

        if source not in self.source_scores:
            self.source_scores[source] = []

        abweichung = abs(price - average)
        self.source_scores[source].append(abweichung)

        # Optional: Durchschnitt der letzten 10 Abweichungen berechnen
        letzte = self.source_scores[source][-10:]
        mean_deviation = sum(letzte) / len(letzte)
        print(f"📊 Quelle: {source} | Abweichung: {abweichung:.4f} | Ø (letzte 10): {mean_deviation:.4f}")

    def get_price_series(self, symbol: str, limit: int = 100) -> List[float]:
        try:
            url = f"https://finnhub.io/api/v1/stock/candle"
            params = {
                "symbol": symbol,
                "resolution": "1",
                "count": limit,
                "token": self.finnhub_key
            }
            response = requests.get(url, params=params)
            data = response.json()
            return data.get("c", [])  # closing prices
        except Exception as e:
            print(f"⚠️ Fehler bei get_price_series (Finnhub): {e}")
            return []

    class FinnhubPriceFetcher:
        def __init__(self, api_key: str):
            self.api_key = api_key

        def get_resolution(self, days: int) -> str:
            if days <= 7:
                return "1"  # 1 Minute
            elif days <= 30:
                return "5"
            elif days <= 90:
                return "15"
            elif days <= 180:
                return "30"
            elif days <= 365:
                return "60"
            else:
                return "D"  # Daily

        def get_price_series(self, symbol: str, days: int = 30) -> pd.DataFrame:
            resolution = self.get_resolution(days)
            end_time = int(time.time())
            start_time = int((datetime.now() - timedelta(days=days)).timestamp())

            url = f"https://finnhub.io/api/v1/stock/candle"
            params = {
                "symbol": symbol,
                "resolution": resolution,
                "from": start_time,
                "to": end_time,
                "token": self.api_key
            }

            try:
                response = requests.get(url, params=params)
                data = response.json()

                if data.get("s") != "ok":
                    print(f"⚠️ Finnhub: Keine Daten für {symbol}")
                    return pd.DataFrame()

                df = pd.DataFrame({
                    "timestamp": pd.to_datetime(data["t"], unit="s"),
                    "open": data["o"],
                    "high": data["h"],
                    "low": data["l"],
                    "close": data["c"],
                    "volume": data["v"]
                })
                df.set_index("timestamp", inplace=True)
                return df

            except Exception as e:
                print(f"❌ Fehler bei Finnhub-Daten für {symbol}: {e}")
                return pd.DataFrame()

    def get_price_series_yfinance(self, epic: str, days: int = 30, interval: str = "1d") -> Optional[pd.DataFrame]:
        try:
            symbol = self.mapping[epic]["yfinance"]
            ticker = yf.Ticker(symbol)

            # Dynamisches Zeitfenster & Intervall bestimmen
            period, interval = get_best_period_interval(days)
            data = ticker.history(period=period, interval=interval)

            if data is not None and not data.empty and "Close" in data.columns:
                data = data.rename(columns={"Close": "close"})
                return data[["close"]]  # Nur Spalte 'close' als DataFrame zurückgeben
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
                    print(f"⚠️ '{source_name}' → DataFrame aber keine gültige 'close'-Spalte oder leer.")
            else:
                print(f"⚠️ '{source_name}' → Ungültiger Typ: {type(s)}")

        if not valid_series:
            print(f"⚠️ Keine gültigen Preisreihen vorhanden – Epic: {epic}")
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
        """
        Wählt automatisch die passende Auflösung für Finnhub basierend auf der Anzahl Tage.
        """
        if days <= 5:
            return "5"  # 5-Minuten-Intervall
        elif days <= 10:
            return "15"
        elif days <= 30:
            return "30"
        elif days <= 90:
            return "60"
        else:
            return "D"  # Daily

    def get_price_series_finnhub(self, epic: str, days: int = 30) -> Optional[pd.DataFrame]:
        """
        Holt historische Preisdaten von Finnhub basierend auf EPIC & Zeitraum.
        Gibt DataFrame mit nur 'close'-Spalte zurück.
        """
        try:
            symbol = self.get_symbol(epic, "finnhub")  # z. B. BTCUSD → BINANCE:BTCUSDT
            resolution = self.get_finnhub_resolution(days)
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

            response = requests.get(url, params=params)
            data = response.json()

            if data.get("s") != "ok":
                print(f"⚠️ Finnhub: Keine Daten für {symbol} ({epic})")
                return None

            df = pd.DataFrame({
                "timestamp": pd.to_datetime(data["t"], unit="s"),
                "close": data["c"]
            })
            df.set_index("timestamp", inplace=True)

            if df.empty:
                print(f"⚠️ Leerer DataFrame von Finnhub für {symbol} ({epic})")
                return None

            return df[["close"]]  # Nur 'close' als DataFrame

        except Exception as e:
            print(f"❌ Fehler beim Abruf von Finnhub-Daten für {epic}: {e}")
            return None

    def get_best_price_series(self, epic: str, days: int = 30) -> Optional[pd.DataFrame]:
        """
        Liefert die beste verfügbare Preisreihe (erst yfinance, dann Fallback Finnhub).
        Automatisch inkl. dynamischer Intervallwahl & Fehlerhandling.
        """
        try:
            interval, _ = get_best_period_interval(days)
            df = self.get_price_series_yfinance(epic, days=days, interval=interval)

            if df is not None and not df.empty:
                print(f"✅ Preisreihe via yfinance geladen für {epic} (Zeilen: {len(df)})")
                # Schreibweise prüfen
                if "Close" in df.columns:
                    df = df.rename(columns={"Close": "close"})
                    print(f"🧼 Spalte 'Close' wurde zu 'close' normalisiert.")
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