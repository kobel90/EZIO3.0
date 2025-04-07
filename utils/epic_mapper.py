import json
import os
from datetime import datetime, timedelta
# utils/epic_mapper.py

import os
import json

def update_epic_mapping(epics: list, pfad="utils/epic_mapping.json"):
    try:
        # Vorhandene Mappings laden
        if os.path.exists(pfad):
            with open(pfad, "r") as f:
                mapping = json.load(f)
        else:
            mapping = {}

        updated = False

        for epic in epics:
            if epic not in mapping:
                # 🧠 Symbol-Logik pro Typ
                is_crypto = epic.endswith("USD") and epic.startswith(("BTC", "ETH", "XRP"))
                is_forex = epic.endswith("USD") and not is_crypto and len(epic) == 6
                is_stock = epic.isalpha() and len(epic) <= 5

                if is_crypto:
                    finnhub_symbol = f"BINANCE:{epic.replace('USD', 'USDT')}"
                    yfinance_symbol = epic.replace("USD", "-USD")
                elif is_forex:
                    finnhub_symbol = f"OANDA:{epic[:3]}_{epic[3:]}"
                    yfinance_symbol = epic + "=X"
                elif is_stock:
                    finnhub_symbol = epic.upper()
                    yfinance_symbol = epic.upper()
                else:
                    finnhub_symbol = epic
                    yfinance_symbol = epic

                mapping[epic] = {
                    "capital": epic,
                    "finnhub": finnhub_symbol,
                    "yfinance": yfinance_symbol
                }

                print(f"🆕 Neues Mapping hinzugefügt: {epic}")
                updated = True

        if updated:
            with open(pfad, "w") as f:
                json.dump(mapping, f, indent=4)
            print("✅ epic_mapping.json aktualisiert.")

    except Exception as e:
        print(f"❌ Fehler beim Aktualisieren des Mappings: {e}")


def lade_epic_mapping(pfad="utils/epic_mapping.json") -> dict:
    try:
        with open(pfad, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Fehler beim Laden der Epic-Mapping-Datei: {e}")
        return {}

def zeige_quota_status(self):
    """Zeigt an, welche Datenquellen aktuell blockiert sind"""
    print("📉 Aktueller Quota-Status:")
    for source, time in self.quota_blocked_until.items():
        if datetime.now() < time:
            print(f"   ⏳ {source} blockiert bis {time.strftime('%H:%M:%S')}")
        else:
            print(f"   ✅ {source} ist wieder verfügbar")