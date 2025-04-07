import json
import os
from datetime import datetime
from typing import Optional
import requests
from datetime import timedelta


class InfoManager:
    def __init__(self, log_path="info_log.json"):
        self.log_path = log_path
        self.quellen_status = {}  # z.B. {"finnhub": {"status": "aktiv", "cooldown_bis": "2025-04-07T12:00:00"}}
        self.cooldown_minuten = 10  # wie lange eine Quelle nach Fehler pausieren soll

        # Neue Quelle-Definition für info_evaluator
        self.quellen = {
            "yfinance": {"status": "aktiv"},
            "finnhub": {"status": "aktiv"},
            "capital": {"status": "aktiv"},
            "newsapi": {"status": "aktiv"},
            "gnews": {"status": "aktiv"},
            "whale_alert": {"status": "aktiv"},
            "cryptobubbles": {"status": "aktiv"},
            "blockchaincenter": {"status": "aktiv"},
        }

        # Prioritäten wie gehabt
        self.prioritaeten = {
            "volumen_spike": ("finnhub", "capital"),
            "kerzen_bewegung": ("yfinance", "finnhub"),
            "news": ("newsapi", "gnews"),
            "tageschart": ("yfinance", "capital"),
            "wochenchart": ("yfinance", "capital"),
            "longterm": ("capital", "yfinance"),
            "whales": ("whale_alert", "finnhub"),
            "marktuebersicht": ("cryptobubbles", "blockchaincenter")
        }

    def klassifiziere_info(self, info_typ: str) -> str:
        schnell = ["volumen_spike", "kerzen_bewegung"]
        mittel = ["tageschart", "news"]
        langsam = ["wochenchart", "longterm", "whales", "marktuebersicht"]

        if info_typ in schnell:
            return "schnell"
        elif info_typ in mittel:
            return "mittel"
        elif info_typ in langsam:
            return "langsam"
        return "unbekannt"

    def get_quellen_prioritaet(self, info_typ: str) -> tuple:
        return self.prioritaeten.get(info_typ, ("unbekannt", "unbekannt"))

    def logge_info(self, asset: str, info_typ: str, gewicht: float, quelle: str, details: Optional[str] = None):
        eintrag = {
            "zeit": datetime.now().isoformat(),
            "asset": asset,
            "typ": info_typ,
            "gewicht": gewicht,
            "quelle": quelle,
            "details": details or "-"
        }

        if not os.path.exists(self.log_path):
            with open(self.log_path, "w") as f:
                json.dump([eintrag], f, indent=4)
        else:
            with open(self.log_path, "r") as f:
                logs = json.load(f)
            logs.append(eintrag)
            with open(self.log_path, "w") as f:
                json.dump(logs, f, indent=4)

    def bewerte_info(self, asset: str, info_typ: str, quelle: str, details: Optional[str] = None) -> float:
        score = 0.5
        if info_typ == "volumen_spike":
            score = 0.8
        elif info_typ == "kerzen_bewegung":
            score = 0.75
        elif info_typ == "news":
            score = 0.6
        elif info_typ == "marktuebersicht":
            score = 0.4

        self.logge_info(asset, info_typ, round(score, 2), quelle, details)
        return round(score, 2)

    def log_infoquelle(self, quelle: str, status: str, score: float):
        print(f"🛰️ Quelle '{quelle}' → Status: {status}, Score: {score}")

        eintrag = {
            "zeit": datetime.now().isoformat(),
            "quelle": quelle,
            "status": status,
            "score": round(score, 2)
        }

        # JSON-Datei (z. B. für GUI-Dashboard)
        logdatei = "quellen_log.json"
        if not os.path.exists(logdatei):
            with open(logdatei, "w") as f:
                json.dump([eintrag], f, indent=4)
        else:
            with open(logdatei, "r") as f:
                alte_logs = json.load(f)
            alte_logs.append(eintrag)
            with open(logdatei, "w") as f:
                json.dump(alte_logs[-200:], f, indent=4)  # Optional: nur letzte 200 Einträge

        # Zusätzlich internes Logging (weiterhin für Bewertung)
        self.logge_info(asset="system", info_typ="quellen_check", gewicht=score, quelle=quelle, details=status)

    def pruefe_quelle(self, quelle: str) -> dict:
        try:
            if quelle == "finnhub":
                response = requests.get("https://finnhub.io/api/v1/quote?symbol=AAPL&token=DEMO")
                status = "aktiv" if response.status_code == 200 else "inaktiv"
                return {"status": status, "bewertung": 0.9}

            elif quelle == "yfinance":
                import yfinance as yf
                data = yf.Ticker("AAPL").info
                status = "aktiv" if "regularMarketPrice" in data else "inaktiv"
                return {"status": status, "bewertung": 0.8}

            elif quelle == "capital":
                # Dummy-Check, da echte Capital.com-API meist Session benötigt
                return {"status": "aktiv", "bewertung": 0.7}

            elif quelle == "newsapi":
                response = requests.get("https://newsapi.org/v2/top-headlines?country=us&apiKey=DEMO")
                status = "aktiv" if response.status_code == 200 else "inaktiv"
                return {"status": status, "bewertung": 0.6}

            elif quelle == "gnews":
                return {"status": "aktiv", "bewertung": 0.5}

            else:
                return {"status": "unbekannt", "bewertung": 0.0}

        except Exception as e:
            print(f"❌ Fehler bei API-Check für {quelle}: {e}")
            return {"status": "fehler", "bewertung": 0.0}

    def _cooldown_zeitpunkt(self) -> str:
        return (datetime.now() + timedelta(minutes=self.cooldown_minuten)).isoformat()

    def markiere_fallback(self, quelle: str):
        cooldown_bis = self._cooldown_zeitpunkt()
        self.quellen_status[quelle] = {"status": "inaktiv", "cooldown_bis": cooldown_bis}
        print(f"⚠️ Quelle {quelle} inaktiv bis {cooldown_bis}")

    def lade_quellen_log(self, max_eintraege: int = 100) -> list:
        """
        Lädt die letzten Einträge aus quellen_log.json zur Auswertung (z. B. GUI).
        """
        logdatei = "quellen_log.json"
        if not os.path.exists(logdatei):
            return []

        try:
            with open(logdatei, "r") as f:
                daten = json.load(f)
            return daten[-max_eintraege:]
        except Exception as e:
            print(f"❌ Fehler beim Laden von quellen_log.json: {e}")
            return []