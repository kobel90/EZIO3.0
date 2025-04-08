import json
import random
import os
import pandas as pd
from colorama import Fore, Style
from datetime import datetime
from typing import List, Dict, Optional, Any
from lernzentrum.lern_interface import LernInterface  # oder je nach Speicheror
from memory_module import MemoryModule
from news_ki import NewsKI
from utils.price_source_manager import PriceSourceManager
from utils.epic_mapper import lade_epic_mapping
from chart_analyzer import ChartAnalyzer
from info_evaluator import InfoEvaluator



class TrendAnalyseKI:
    """Einfache Trendanalyse: Prüft auf 5 steigende oder fallende Werte"""
    def analysiere_trend(self, preise: List[float]) -> str:
        if len(preise) < 5:
            return "NEUTRAL"
        letzte = preise[-5:]
        if all(x < y for x, y in zip(letzte, letzte[1:])):
            return "UP"
        if all(x > y for x, y in zip(letzte, letzte[1:])):
            return "DOWN"
        return "NEUTRAL"


class VolatilitaetsKI:
    """Berechnet durchschnittliche Preisbewegung und schätzt Trade-Dauer"""
    def schaetze_volatilitaet(self, preise: List[float]) -> float:
        if len(preise) < 2:
            return 0.0
        bewegungen = [abs(preise[i] - preise[i - 1]) for i in range(1, len(preise))]
        return round(sum(bewegungen) / len(bewegungen), 4)

    def schaetze_trade_dauer(self, vola: float) -> int:
        if vola > 1:
            return 5
        elif vola > 0.5:
            return 15
        return 30


class TradingKI:
    """
    Hauptklasse für die Trading-KI.
    Nutzt Trend-, Volatilitäts-, Memory- & News-Komponenten zur Signalgebung.
    """

    def __init__(self):
        self.signals: List[Dict[str, Any]] = []
        self.epic_configs: Dict[str, Dict[str, Any]] = {}
        self.confidence_scores: Dict[str, float] = {}

        self.chart_analyzer = ChartAnalyzer()
        self.trend_ki = TrendAnalyseKI()
        self.vola_ki = VolatilitaetsKI()
        self.memory = MemoryModule()
        self.info_evaluator = InfoEvaluator()
        self.news_ki = NewsKI()
        self.lerninterface = LernInterface()
        self.strategy_mode = "mixed"  # Optionen: classic, confidence, news, mixed
        self.price_mapper = PriceSourceManager()
        self.price_manager = PriceSourceManager()
        self.price_source_manager = PriceSourceManager()
        self.mapping = lade_epic_mapping()

    def normalisiere_epic(self, epic: str) -> dict:
        """
        Gibt ein Dict mit den passenden Symbolen für alle Quellen zurück.
        {
            "capital": "BTCUSD",
            "finnhub": "BINANCE:BTCUSDT",
            "yfinance": "BTCUSD"
        }
        """
        symbol_info = self.price_manager.mapping.get(epic, {
            "capital": epic,
            "yfinance": epic
        })
        return symbol_info

    def analysiere_signal(self, daten: Dict) -> Optional[str]:
        epic = daten.get("epic", "UNBEKANNT")
        preise = daten.get("preise", [])

        if not isinstance(preise, list) or len(preise) < 10:
            self.memory.speichere_ereignis(epic, "❌ Ungültige oder zu wenig Preisdaten")
            return None

        try:
            trend = self.trend_ki.analysiere_trend(preise)
        except Exception as e:
            self.memory.speichere_ereignis(epic, f"❌ Fehler bei Trendanalyse: {e}")
            return None

        try:
            vola = self.vola_ki.schaetze_volatilitaet(preise)
        except Exception as e:
            self.memory.speichere_ereignis(epic, f"❌ Fehler bei Volatilitätsanalyse: {e}")
            return None

        try:
            confidence = self.bewerte_confidence(epic, daten)
        except Exception as e:
            self.memory.speichere_ereignis(epic, f"❌ Fehler bei Confidence-Bewertung: {e}")
            return None

        try:
            news_score = self.news_ki.analysiere_nachrichten(epic, daten.get("nachrichten", []))
        except Exception as e:
            self.memory.speichere_ereignis(epic, f"❌ Fehler bei News-Analyse: {e}")
            news_score = 0.5  # neutral

        print(
            f"🧠 Modus: {self.strategy_mode} | News: {news_score:.2f} | Trend: {trend} | Vola: {vola:.2f} | Conf: {confidence:.2f}")

        # 📌 Strategie-Logik
        try:
            if self.strategy_mode == "news":
                if news_score > 0.7:
                    self.memory.speichere_ereignis(epic, "📰 Positiv-News-Signal")
                    return "BUY"
                elif news_score < 0.3:
                    self.memory.speichere_ereignis(epic, "📰 Negativ-News-Signal")
                    return "SELL"

            elif self.strategy_mode == "confidence":
                if confidence >= 0.7:
                    richtung = "BUY" if trend == "UP" else "SELL"
                    self.memory.speichere_ereignis(epic, f"⭐️ Conf-Signal ({confidence})")
                    return richtung

            elif self.strategy_mode == "classic":
                if trend == "UP" and vola > 0.3:
                    return "BUY"
                if trend == "DOWN" and vola > 0.3:
                    return "SELL"

            elif self.strategy_mode == "mixed":
                if news_score > 0.6 and confidence >= 0.6 and trend in ["UP", "DOWN"]:
                    richtung = "BUY" if trend == "UP" else "SELL"
                    self.memory.speichere_ereignis(epic, f"🧩 Mixed-Modus-Signal: {richtung}")
                    return richtung

        except Exception as e:
            self.memory.speichere_ereignis(epic, f"❌ Strategiefehler: {e}")

        return None

    def get_externes_symbol(self, epic: str, quelle: str) -> str:
        """
        Gibt das umgerechnete Symbol für eine externe Datenquelle (z. B. 'finnhub' oder 'yfinance') zurück.
        """
        return self.price_mapper.get_symbol(epic, quelle)

    def bewerte_confidence(self, epic: str, daten: Dict) -> float:
        """
        Bewertet die Gesamtzuversicht (Confidence) für einen Trade:
        Kombination aus technischen Indikatoren und News-Stimmung.
        """
        score = 0

        def get_val(value, default=0.0):
            if isinstance(value, pd.Series):
                return value.iloc[-1] if not value.empty else default
            return value if value is not None else default

        macd = get_val(daten.get("macd"), 0)
        signal = get_val(daten.get("signal"), 0)
        rsi = get_val(daten.get("rsi"), 50)
        volumen = get_val(daten.get("volumen"), 0)
        volumen_schnitt = get_val(daten.get("volumen_schnitt"), 1)
        preis = get_val(daten.get("preis"), 0)
        support = get_val(daten.get("support"), -999)

        if macd > signal:
            score += 1
        if rsi < 45:
            score += 1
        if volumen > volumen_schnitt * 1.2:
            score += 1
        if preis < support + 0.3:
            score += 1

        # Newsbewertung
        letzte_news = self.news_ki.zeige_newsverlauf(epic)[-1:]
        if letzte_news:
            news_daten = self.news_ki.analysiere_nachricht(epic, letzte_news[0])
            sentiment = news_daten.get("sentiment", "")
            if sentiment == "bullish":
                score += 1
            elif sentiment == "bearish":
                score -= 1

        confidence = round(score / 5.0, 2)
        return confidence

    def berechne_trade_groesse(self, epic: str, kapital: float, confidence: float) -> Dict[str, float]:
        """
        Berechnet die Trade-Größe unter Berücksichtigung von Kapital & Confidence.
        - max 40 % von 80 % von 2/3 Kapital
        """
        config = self.get_config(epic)
        min_deal_size = config.get("minDealSize", 1.0)
        preis = config.get("preis", 1.0)

        max_einsatz = kapital * 0.4
        einsatz = max_einsatz * confidence
        anzahl = einsatz / preis
        anzahl = max(min_deal_size, round(anzahl / min_deal_size) * min_deal_size)

        self.memory.speichere_ereignis(epic, f"💸 Trade-Größe: {anzahl} bei {preis} (Conf={confidence})")
        return {
            "anzahl": anzahl,
            "preis": preis,
            "confidence": confidence,
            "max_einsatz": max_einsatz,
            "eingesetztes_kapital": einsatz,
            "min_deal_size": min_deal_size
        }

    def schaetze_trade_dauer(self, epic: str, daten: Dict) -> int:
        """
        Schätzt die Trade-Dauer basierend auf Volatilität der letzten Preise.
        """
        preise = daten.get("preise", [])
        vola = self.vola_ki.schaetze_volatilitaet(preise)
        dauer = self.vola_ki.schaetze_trade_dauer(vola)
        self.memory.speichere_ereignis(daten["epic"], f"⏱ Dauer geschätzt: {dauer} Min (Vola: {vola:.2f})")
        return dauer

    def risikobewertung(self, epic: str, confidence: float, vola: float) -> str:
        """
        Gibt einen Risiko-Score zurück: 'NIEDRIG', 'MITTEL', 'HOCH'
        Basierend auf Confidence + Volatilität
        """
        score = confidence + (1 if vola < 0.3 else 0.5 if vola < 0.6 else 0.2)

        if score >= 1.4:
            risiko = "NIEDRIG"
        elif score >= 1.0:
            risiko = "MITTEL"
        else:
            risiko = "HOCH"

        self.memory.speichere_ereignis(epic, f"📊 Risikobewertung: {risiko} (Score={score:.2f})")
        return risiko

    def speichere_signal(self, epic: str, richtung: str, confidence: float = 0.8):
        signal = {
            "epic": epic,
            "richtung": richtung,
            "confidence": confidence,
            "zeitpunkt": datetime.now().isoformat()
        }
        self.signals.append(signal)
        self.memory.speichere_ereignis(epic, f"📩 Signal gespeichert: {richtung}, Confidence: {confidence}")

    def gib_signal(self, epic: str) -> Optional[Dict[str, str]]:
        """
        Gibt das letzte gespeicherte Signal für einen EPIC zurück (wenn vorhanden).
        """
        for eintrag in reversed(self.signals):
            if eintrag.get("epic") == epic:
                return eintrag
        return None

    def liste_signale(self) -> List[Dict[str, str]]:
        return self.signals[-10:]

    def loesche_signale(self):
        self.signals.clear()
        print("🧹 Alle Signale gelöscht.")

    def update_config(self, epic: str, config: Dict[str, Any]):
        self.epic_configs[epic] = config
        self.memory.speichere_ereignis(epic, f"⚙️ Konfiguration aktualisiert: {config}")

    def get_config(self, epic: str) -> Dict[str, Any]:
        return self.epic_configs.get(epic, {})

    def auswertung_memory(self, epic: str):
        """
        Gibt die letzten gespeicherten Events aus der Memory-Komponente zurück.
        """
        eintraege = self.memory.zeige_verlauf(epic)
        print(f"🧠 Memory-Verlauf für {epic}:")
        for eintrag in eintraege[-5:]:
            print(f" – {eintrag}")

    def zeige_analysebericht(self, epic: str):
        """
        Zeigt eine kompakte Übersicht der letzten Analyse + Memory-Einträge für den gewählten EPIC.
        """
        signal = self.gib_signal(epic)
        eintraege = self.memory.zeige_verlauf(epic)

        print("\n📊 Analysebericht")
        print(f"📌 EPIC: {epic}")
        print("📂 Letztes Signal:")
        if signal:
            print(f"   ➤ Richtung: {signal['richtung']}")
            print(f"   ➤ Confidence: {signal['confidence']}")
            print(f"   ➤ Zeitpunkt: {signal['zeitpunkt']}")
        else:
            print("   ⚠️ Kein gültiges Signal gefunden.")

        print("\n🧠 Memory-Log (letzte 5 Einträge):")
        for eintrag in eintraege[-5:]:
            print(f"   – {eintrag}")
        print("\n────────────────────────────\n")

    def importiere_konfigurationen(self, pfad: str = "trading_ki_config.json"):
        """
        Lädt Konfigurationen und Memory-Verlauf aus einer JSON-Datei.
        """
        try:
            with open(pfad, "r") as f:
                daten = json.load(f)
                self.epic_configs = daten.get("epic_configs", {})
                self.memory.lade_aus_dict(daten.get("memory", {}))
            print(f"📥 Konfigurationen erfolgreich geladen aus '{pfad}'")
        except Exception as e:
            print(f"❌ Fehler beim Import: {e}")

    def exportiere_konfigurationen(self, pfad: str = "trading_ki_config.json"):
        """
        Exportiert alle Konfigurationen und Memory-Verlauf in eine JSON-Datei.
        """
        try:
            daten = {
                "epic_configs": self.epic_configs,
                "memory": self.memory.speichere_als_dict()
            }
            with open(pfad, "w") as f:
                json.dump(daten, f, indent=4)
            print(f"💾 Konfigurationen erfolgreich gespeichert in '{pfad}'")
        except Exception as e:
            print(f"❌ Fehler beim Export: {e}")

    def verarbeite_trade_resultat(self, epic: str, resultat: Dict[str, float]):
        """
        Verarbeitet das Ergebnis eines abgeschlossenen Trades und lernt daraus.
        Erwartet ein Dict mit 'gewinn' (float) und optional 'dauer' (int).
        """
        gewinn = resultat.get("gewinn", 0.0)
        dauer = resultat.get("dauer", None)

        if epic not in self.epic_configs:
            self.epic_configs[epic] = {}

        config = self.epic_configs[epic]

        # Zähle Gewinne/Verluste
        if gewinn >= 0:
            config["erfolgreiche_trades"] = config.get("erfolgreiche_trades", 0) + 1
        else:
            config["fehltrades"] = config.get("fehltrades", 0) + 1

        # Strategie-Anpassung: erhöhe/deckele confidence
        alt_conf = config.get("basis_confidence", 0.75)
        if gewinn >= 0:
            neue_conf = min(1.0, alt_conf + 0.01)
        else:
            neue_conf = max(0.5, alt_conf - 0.02)

        config["basis_confidence"] = neue_conf

        self.epic_configs[epic] = config
        self.memory.speichere_ereignis(epic, f"📊 Trade abgeschlossen: {gewinn:.2f} CHF → Neue Confidence: {neue_conf:.2f}")

    def korrektur_nach_fehltrade(self, epic: str):
        """
        Reagiert auf einen fehlgeschlagenen Trade, um Fehlerquellen im Memory zu markieren.
        Beispiel: Letztes Signal war falsch, Confidence zu hoch etc.
        """
        letzter_eintrag = self.gib_signal(epic)
        if not letzter_eintrag:
            return

        confidence = letzter_eintrag.get("confidence", 0.5)
        if confidence >= 0.8:
            fehler_meldung = f"⚠️ Hohes Vertrauen trotz Verlust – möglicher Analysefehler"
        else:
            fehler_meldung = f"❌ Fehltrade mit moderater Confidence – Strategie prüfen"

        self.memory.speichere_ereignis(epic, fehler_meldung)

    def verarbeite_news(self, epic: str, nachrichten: List[str]):
        """
        Nutzt die News-KI, um Einfluss von Nachrichten auf das EPIC zu bewerten.
        Anpassung des Confidence-Scores & Logging.
        """
        score = self.news_ki.analysiere_nachrichten(epic, nachrichten)

        if score > 0.7:
            self.memory.speichere(epic, {"news": "positiv", "news_score": score})
            self.erhoehe_confidence(epic, faktor=score)
            print(f"📰 {epic}: Positive News erkannt (Score {score}) → Confidence erhöht.")
        elif score < 0.3:
            self.memory.speichere(epic, {"news": "negativ", "news_score": score})
            self.senke_confidence(epic, faktor=(1 - score))
            print(f"📰 {epic}: Negative News erkannt (Score {score}) → Confidence gesenkt.")
        else:
            self.memory.speichere(epic, {"news": "neutral", "news_score": score})

    def erhoehe_confidence(self, epic: str, faktor: float = 0.1):
        self.confidence_scores[epic] = min(1.0, self.confidence_scores.get(epic, 0.5) + 0.1 * faktor)

    def senke_confidence(self, epic: str, faktor: float = 0.1):
        self.confidence_scores[epic] = max(0.0, self.confidence_scores.get(epic, 0.5) - 0.1 * faktor)

    def zeige_analyse(self, epic: str, datenpaket: dict):
        print(f"🧠 KI-Analyse {epic}: {datenpaket}")

    def bewerte_risiko(self, epic: str, datenpaket: dict) -> float:
        """
        Temporäre Dummy-Risikobewertung zwischen 0.0 (kein Risiko) und 1.0 (hohes Risiko).
        Später durch echte Analyse ersetzen.
        """
        return round(random.uniform(0.2, 0.8), 2)  # Zufallswert für realistisches Testen

    def lerne_von_webseite(self, url: str):
        print(f"🌐 Lade und analysiere Webseite: {url}")
        text = self.lerninterface.lade_webseite(url)
        if text:
            self.lerne_aus_text(text, quelle=url)

    def lerne_aus_ordner(self, ordnerpfad: str):
        """
        Liest alle .txt- und .html-Dateien in einem Ordner, analysiert sie und speichert den Inhalt.
        """
        if not os.path.exists(ordnerpfad):
            print(f"❌ Ordner nicht gefunden: {ordnerpfad}")
            return

        dateien = [f for f in os.listdir(ordnerpfad) if f.endswith(".txt") or f.endswith(".html")]
        gesamt = len(dateien)
        if gesamt == 0:
            print(f"⚠️ Keine passenden Textdateien gefunden in {ordnerpfad}")
            return

        print(f"\n📂 Lernprozess gestartet – {gesamt} Dateien gefunden:\n")

        for i, datei in enumerate(dateien, start=1):
            pfad = os.path.join(ordnerpfad, datei)
            try:
                with open(pfad, "r", encoding="utf-8") as f:
                    inhalt = f.read()

                    if datei.endswith(".html"):
                        from bs4 import BeautifulSoup
                        soup = BeautifulSoup(inhalt, "html.parser")
                        inhalt = soup.get_text()

                    self.lerne_aus_text(inhalt, quelle=f"Datei: {datei}")
                    print(f"✅ [{i}/{gesamt}] Gelernt aus: {datei}")
            except Exception as e:
                print(f"⚠️ [{i}/{gesamt}] Fehler bei {datei}: {e}")

        print(f"\n🎉 Lernprozess abgeschlossen. {gesamt} Dateien verarbeitet.\n")

    def lerne_aus_datei(self, dateipfad: str, quelle: str = "Datei"):
        """
        Liest eine Textdatei ein und übergibt den Inhalt an den Lernmechanismus.
        """
        if not os.path.exists(dateipfad):
            print(f"❌ Datei nicht gefunden: {dateipfad}")
            return

        try:
            with open(dateipfad, "r", encoding="utf-8") as f:
                text = f.read()

            self.lerne_aus_text(text, quelle=quelle)
            print(f"📥 Datei erfolgreich verarbeitet: {dateipfad}")

        except Exception as e:
            print(f"⚠️ Fehler beim Einlesen der Datei: {e}")

    def lerne_aus_text(self, text: str, quelle: str = "manuell"):
        """
        Analysiert und speichert einen Text im Memory.
        Später erweiterbar mit NLP oder Embeddings.
        """
        print(f"📚 Lerne aus Text ({quelle}): {text[:60]}...")

        # 🧠 Textanalyse durchführen
        analyse = self.lerninterface.analysiere_text(text)

        # 📦 Signal-Daten vorbereiten
        signal = {
            "quelle": quelle,
            "inhalt": text,
            "analyse": analyse,
            "zeit": datetime.now().isoformat()
        }

        # 💾 Speichern im Memory-Modul
        self.memory.speichere("lerntext", signal)

        print(f"✅ Lernsignal gespeichert ({quelle}) mit Analyse: {analyse}")

        if signal not in self.memory.gespeicherte_daten.get("lerntext", []):
            self.memory.speichere("lerntext", signal)
        else:
            print("⚠️ Lernsignal bereits vorhanden, wird übersprungen.")

    def zeige_lernverlauf(self, epic: str = "lerntext"):
        """
        Gibt alle gespeicherten Lerntexte oder Signale für ein Epic aus.
        """
        eintraege = self.memory.lade_verlauf(epic)
        if not eintraege:
            print(f"📭 Kein Lernverlauf für {epic} gefunden.")
            return

        print(f"\n📚 Lernverlauf für {epic} ({len(eintraege)} Einträge):")
        for eintrag in sorted(eintraege, key=lambda e: e.get("zeit", ""), reverse=True):
            zeit = eintrag.get("zeit", "unbekannt")
            quelle = eintrag.get("quelle", "unbekannt")
            inhalt = eintrag.get("inhalt", "")[:80]  # nur ersten Teil
            print(f"🕒 {zeit} | Quelle: {quelle} | Text: {inhalt}...")

    from datetime import datetime
    from typing import Dict, Any, Optional

    def generiere_signal(self, epic: str, daten: Dict, kapital: float) -> Optional[Dict[str, Any]]:
        try:
            # 🔍 Richtung aus interner Analyse
            richtung = self.analysiere_signal(daten)
            if not richtung:
                return None

            # 🧠 EPIC-Mapping abrufen
            symbol_info = self.normalisiere_epic(epic)
            symbol_finnhub = symbol_info.get("finnhub", epic)
            symbol_yfinance = symbol_info.get("yfinance", epic)

            # 📈 Chartdaten abrufen
            chart_df = self.price_source_manager.get_best_price_series(epic, days=30)
            chartinfo = {}

            # ✅ Robuste Chartanalyse mit Debug
            try:
                print(f"\n📊 DEBUG START für {epic}")

                if chart_df is None or chart_df.empty:
                    print("❌ chart_df ist None oder leer – Signal wird abgebrochen.")
                    self.memory.speichere_ereignis(epic, "❌ Keine Chartdaten (None/leer)")
                    return None

                print(f"🔎 Spalten im chart_df: {list(chart_df.columns)}")
                print(f"🧪 chart_df.head():\n{chart_df.head()}")

                # 🧼 Schreibweise vereinheitlichen (Close → close)
                for col in chart_df.columns:
                    if col.lower() == "close":
                        chart_df = chart_df.rename(columns={col: "close"})
                        print(f"✅ Spalte '{col}' wurde zu 'close' normalisiert.")
                        break

                if "close" not in chart_df.columns:
                    raise ValueError("'close'-Spalte fehlt (nach Normalisierung)")

                # 🧠 Analyse durchführen
                chartinfo = self.chart_analyzer.analysiere_chartverlauf(chart_df)
                print(f"📈 Analyse erfolgreich für {epic}: {chartinfo}")

            except Exception as e:
                print(f"⚠️ Fehler bei Chartanalyse ({epic}): {e}")
                self.memory.speichere_ereignis(epic, f"❌ Chartanalyse fehlgeschlagen: {e}")
                chartinfo = {}  # Fallback

            # 🎯 KI-Bewertungen
            confidence = self.bewerte_confidence(epic, daten)
            dauer = self.schaetze_trade_dauer(epic, daten)
            vola = self.vola_ki.schaetze_volatilitaet(daten.get("preise", []))
            risiko = self.risikobewertung(epic, confidence, vola)
            groesse = self.berechne_trade_groesse(epic, kapital, confidence)

            # 📦 Signal zusammenbauen
            signal = {
                "epic": epic,
                "direction": richtung,
                "size": groesse,
                "confidence": confidence,
                "dauer": dauer,
                "risiko": risiko,
                "zeit": datetime.now().isoformat(),
                "symbol_finnhub": symbol_finnhub,
                "symbol_yfinance": symbol_yfinance,
            }

            # 🔁 Chartinfo mergen (falls vorhanden)
            signal.update(chartinfo)

            # 🧠 In Liste speichern (max. 5)
            self.signals.append(signal)
            if len(self.signals) > 5:
                self.signals.pop(0)

            # 💾 Im Memory speichern
            self.memory.speichere(epic, {
                "typ": "signal",
                **signal
            })

            print(f"📦 Generiertes Signal gespeichert: {signal}")
            return signal

        except Exception as fehler:
            print(f"❌ Fehler bei Signal für {epic}: {fehler}")
            self.memory.speichere_ereignis(epic, f"❌ Fehler beim Signal: {fehler}")
            import traceback
            traceback.print_exc()
            return None


    def get_latest_signals(self, anzahl: int = 10) -> List[Dict[str, Any]]:
        """
        Gibt die letzten N Signale zurück – z. B. für Visualisierung, Export oder GUI.
        """
        return self.signals[-anzahl:]

    def lade_strategy_modus(self, pfad: str = "strategie_modus.txt"):
        """
        Liest den gewünschten Strategiemodus aus einer Datei.
        So kann der Modus live gewechselt werden.
        """
        try:
            if not os.path.exists(pfad):
                return  # Keine Datei vorhanden – Standardmodus bleibt

            with open(pfad, "r") as f:
                modus = f.read().strip().lower()
                if modus in ["classic", "confidence", "news", "mixed"]:
                    self.strategy_mode = modus
                    print(f"🔁 Strategie-Modus geändert zu: {modus.upper()}")
                else:
                    print(f"⚠️ Ungültiger Modus in Datei: {modus}")
        except Exception as e:
            print(f"❌ Fehler beim Laden des Strategie-Modus: {e}")

    def automatischer_moduswechsel(self, performance: float = 0.0, uhrzeit: Optional[datetime] = None):
        uhrzeit = uhrzeit or datetime.now()
        stunde = uhrzeit.hour

        neuer_modus = self.strategy_mode

        if stunde < 9:
            neuer_modus = "classic"
        elif performance < -50:
            neuer_modus = "defensiv"
        elif performance > 200:
            neuer_modus = "aggressiv"
        else:
            letzter_news_score = self.news_ki.analysiere_nachrichten("MARKT", ["general news"])
            if letzter_news_score > 0.7:
                neuer_modus = "confidence"
            elif letzter_news_score < 0.3:
                neuer_modus = "classic"

        if neuer_modus != self.strategy_mode:
            print(f"🔁 Automatischer Moduswechsel: {self.strategy_mode} ➤ {neuer_modus}")
            self.strategy_mode = neuer_modus

        # ✅ Chartdaten holen und analysieren
        chart_df = self.price_manager.get_best_price_series("BTCUSD", days=30)
        if chart_df is not None and not chart_df.empty:
            chartinfo = self.chart_analyzer.analysiere_chartverlauf(chart_df)
            print(f"📈 Chartinfo: {chartinfo}")

    def lern_logik(self, epic, quelle):
        self.memory.log_preisquelle(epic, quelle)
