import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from lernzentrum.lern_interface import LernInterface
from news_ki import NewsKI
from memory_module import MemoryModule
from utils.price_source_manager import PriceSourceManager
from utils.epic_mapper import lade_epic_mapping
from info_manager import InfoManager
from strategie_engineV2 import (
    ermittle_richtung,
    schaetze_trade_dauer,
    berechne_volatilitaet_preise,
    ist_einstieg_geeignet
)

class InfoEvaluator:
    def __init__(self):
        self.signals: List[Dict[str, Any]] = []
        self.epic_configs: Dict[str, Dict[str, Any]] = {}
        self.confidence_scores: Dict[str, float] = {}

        self.memory = MemoryModule()
        self.news_ki = NewsKI()
        self.lerninterface = LernInterface()

        self.strategy_mode = "mixed"  # Optionen: classic, confidence, news, mixed
        self.info_mode = "standard"  # Optionen: standard, deepfilter, backup

        self.price_mapper = PriceSourceManager()
        self.price_manager = PriceSourceManager()
        self.price_source_manager = PriceSourceManager()
        self.mapping = lade_epic_mapping()
        self.manager = InfoManager()
        self.memory_log = []
        self.check_interval = 60

    def generiere_signal(self, daten: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        epic = daten.get("epic", "UNKNOWN")

        richtung = self.analysiere_signal(daten)
        if not richtung:
            return None

        confidence = daten.get("confidence", 0.5)
        dauer = schaetze_trade_dauer(daten)
        risiko = daten.get("risiko", 0.5)

        wichtigkeit = self.bewerte_information(epic, daten)
        if wichtigkeit >= 0.7:
            self.memory.speichere_ereignis(epic, f"📌 Wichtige Info erkannt (Score: {wichtigkeit})")

        return {
            "epic": epic,
            "direction": richtung,
            "confidence": confidence,
            "dauer": dauer,
            "risiko": risiko,
            "wichtigkeit": wichtigkeit
        }

    def analysiere_signal(self, daten: Dict) -> Optional[str]:
        epic = daten.get("epic", "UNBEKANNT")
        preise = daten.get("preise", [])

        if len(preise) < 10:
            self.memory.speichere_ereignis(epic, "❌ Zu wenig Preisdaten")
            return None

        trend = ermittle_richtung(daten)
        vola = berechne_volatilitaet_preise(preise)
        confidence = daten.get("confidence", 0.5)
        news_score = self.news_ki.analysiere_nachrichten(epic, daten.get("nachrichten", []))
        wichtigkeit = self.bewerte_information(epic, daten)

        if wichtigkeit >= 0.7:
            self.memory.speichere_ereignis(epic, f"📌 Info-Evaluator: wichtig ({wichtigkeit})")

        print(
            f"🧠 Modus: {self.strategy_mode} | News: {news_score:.2f} | Trend: {trend} | Vola: {vola:.2f} | Conf: {confidence:.2f} | Info: {wichtigkeit:.2f}")

        if self.strategy_mode == "news":
            if news_score > 0.7:
                self.memory.speichere_ereignis(epic, "📸 Positiv-News-Signal")
                return "BUY"
            elif news_score < 0.3:
                self.memory.speichere_ereignis(epic, "📸 Negativ-News-Signal")
                return "SELL"
            else:
                return None

        elif self.strategy_mode == "confidence":
            if confidence >= 0.7:
                richtung = "BUY" if trend == "UP" else "SELL"
                self.memory.speichere_ereignis(epic, f"⭐️ Conf-Signal ({confidence})")
                return richtung
            else:
                return None

        elif self.strategy_mode == "classic":
            if trend == "UP" and vola > 0.3:
                return "BUY"
            if trend == "DOWN" and vola > 0.3:
                return "SELL"
            return None

        elif self.strategy_mode == "mixed":
            if news_score > 0.6 and confidence >= 0.6 and trend in ["UP", "DOWN"]:
                richtung = "BUY" if trend == "UP" else "SELL"
                self.memory.speichere_ereignis(epic, f"🧙 Mixed-Modus-Signal: {richtung}")
                return richtung
            else:
                return None

        return None

    def bewerte_information(self, epic: str, daten: Dict[str, Any]) -> float:
        score = 0.0
        if daten.get("volumen", 0) > daten.get("volumen_schnitt", 1) * 1.3:
            score += 0.3
        if daten.get("rsi", 50) < 30:
            score += 0.2
        if daten.get("price", 0) > daten.get("ema200", 9999):
            score += 0.2
        if daten.get("news_score", 0) > 0.7:
            score += 0.3
        return min(score, 1.0)

    def evaluate_all_sources(self):
        for quelle in self.manager.quellen.keys():
            try:
                result = self.manager.pruefe_quelle(quelle)
                self.manager.log_infoquelle(quelle, result.get("status", "keine Antwort"), result.get("bewertung", 0))
                if result.get("status") != "aktiv":
                    self.manager.markiere_fallback(quelle)
            except Exception as e:
                self.manager.log_infoquelle(quelle, "Fehler", 0)
                print(f"❌ Fehler bei Quelle {quelle}: {e}")

    def loop(self):
        while True:
            print(f"🔄 Quellenbewertung startet – {datetime.now().strftime('%H:%M:%S')}...")
            self.evaluate_all_sources()
            time.sleep(self.check_interval)

    def log_lernbewertung(self, quelle: str, inhalt: str, score: float):
        eintrag = {
            "zeit": datetime.now().isoformat(),
            "quelle": quelle,
            "score": score,
            "inhalt": inhalt[:200]
        }
        self.memory_log.append(eintrag)
        self._speichere_logdatei()

    def _speichere_logdatei(self):
        try:
            with open("lernlog.json", "w") as f:
                import json
                json.dump(self.memory_log, f, indent=2)
        except Exception as e:
            print(f"❌ Fehler beim Speichern des Lernlogs: {e}")

if __name__ == "__main__":
    evaluator = InfoEvaluator()
    evaluator.loop()