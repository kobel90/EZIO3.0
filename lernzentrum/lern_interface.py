# lern_interface.py

import os
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime

class LernInterface:
    def __init__(self, speicherpfad="lernarchiv/", quellen_pfad="lernarchiv/quellen/"):
        self.speicherpfad = speicherpfad
        self.quellen_pfad = quellen_pfad
        os.makedirs(self.speicherpfad, exist_ok=True)
        os.makedirs(self.quellen_pfad, exist_ok=True)

    def speichere_text(self, text: str, quelle: str = "manuell"):
        datum = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        dateiname = f"{self.speicherpfad}{datum}_{quelle}.txt"
        with open(dateiname, "w") as f:
            f.write(text)
        print(f"✅ Text gespeichert als: {dateiname}")
        return dateiname

    def lade_webseite(self, url: str) -> str:
        try:
            response = requests.get(url)
            soup = BeautifulSoup(response.text, "html.parser")
            text = soup.get_text()
            print(f"🌐 Webseite geladen: {url}")
            return text
        except Exception as e:
            print(f"❌ Fehler beim Laden der Webseite: {e}")
            return ""

    def analysiere_text(self, text: str) -> dict:
        from collections import Counter

        worte = text.lower().split()

        # 🔢 Kategorie-Scores
        score = {
            "risiko": sum(w in worte for w in ["warnung", "risiko", "verlust", "crash"]),
            "chancen": sum(w in worte for w in ["gewinn", "profit", "steigt", "positiv"]),
            "strategie": sum(w in worte for w in ["strategie", "setup", "einstieg", "ausstieg"]),
        }

        # 🔑 Keywords (alle gezählt)
        keywords = [
            "kursziel", "gewinn", "verlust", "volumen", "breakout", "widerstand", "unterstützung",
            "verkauf", "kauf", "short", "long", "trend", "crash", "whales", "einstieg", "ausbruch"
        ]
        gefunden = [wort for wort in worte if wort in keywords]
        keyword_count = dict(Counter(gefunden))

        # 📐 Strukturinformationen
        zeilen = text.strip().splitlines()
        abschnitte = len([z for z in zeilen if z.strip()])
        saetze = text.count(".") + text.count("!") + text.count("?")

        # 😊 Stimmung (Positiv/Negativ-Wert)
        sentiment = score["chancen"] - score["risiko"]

        # 📊 Konsolidiertes Ergebnis
        analyse = {
            "score": score,
            "sentiment_score": sentiment,
            "keywords": keyword_count,
            "struktur": {
                "abschnitte": abschnitte,
                "saetze": saetze,
                "zeichen": len(text)
            }
        }

        print(f"📊 Analyse-Ergebnis:\n{analyse}")
        return analyse

    def autodurchlauf(self, ki):
        """
        Lässt die KI automatisch aus allen Textdateien im Quellenordner lernen.
        """
        if not os.path.exists(self.quellen_pfad):
            print("📁 Kein Quellenordner gefunden.")
            return

        dateien = [f for f in os.listdir(self.quellen_pfad) if f.endswith(".txt")]
        if not dateien:
            print("📭 Keine Textquellen gefunden.")
            return

        for datei in dateien:
            pfad = os.path.join(self.quellen_pfad, datei)
            try:
                with open(pfad, "r", encoding="utf-8") as file:
                    inhalt = file.read()
                    print(f"📘 Lerne aus {datei} ({len(inhalt)} Zeichen)")
                    ki.lerne_aus_text(inhalt, quelle=datei)
            except Exception as e:
                print(f"⚠️ Fehler beim Lesen von {datei}: {e}")