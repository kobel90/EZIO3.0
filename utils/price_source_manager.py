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
        series = self.get_price_series_yfinance(epic, days)
        if series is not None and "close" in series.columns:
            return series["close"]
        print(f"⚠️ Keine gültige Preisreihe für {epic}")
        return None

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

    def get_best_price_series(self, epic: str, days: int = 30) -> Optional[pd.DataFrame]:
        try:
            df = self.get_price_series_yfinance(epic, days=days)
            if df is not None and not df.empty:
                print(f"✅ Preisreihe via yfinance geladen für {epic} (Zeilen: {len(df)})")
                return df
            raise ValueError("Keine gültige Preisreihe über yfinance gefunden.")
        except Exception as e:
            print(f"❌ Fehler beim Laden der Preisreihe für {epic}: {e}")
            return None
