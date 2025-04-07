from typing import List, Dict


class NewsKI:
    """
    Analysiert Nachrichten (Textliste) und liefert einen Einflussfaktor (0.0 = negativ, 1.0 = positiv).
    """

    def __init__(self):
        self.keywords = {
            "positive": ["bullish", "growth", "beats expectations", "record", "upgrade", "surge"],
            "negative": ["bearish", "miss", "crash", "lawsuit", "bankruptcy", "downgrade"]
        }

    def analysiere_nachrichten(self, epic: str, nachrichten: List[str]) -> float:
        """
        Analysiert Nachrichten zu einem EPIC und berechnet einen normierten Einflussfaktor.

        :param epic: Markt-EPIC (z. B. AAPL)
        :param nachrichten: Liste von Nachrichten-Texten
        :return: Score zwischen 0.0 (negativ) und 1.0 (positiv)
        """
        score = 0
        gesamt = 0

        for text in nachrichten:
            text = text.lower()
            for pos in self.keywords["positive"]:
                if pos in text:
                    score += 1
                    gesamt += 1
            for neg in self.keywords["negative"]:
                if neg in text:
                    score -= 1
                    gesamt += 1

        if gesamt == 0:
            return 0.5  # neutraler Einfluss

        normiert = (score / gesamt + 1) / 2  # Skaliert auf Bereich 0.0 bis 1.0
        return round(normiert, 2)

    def stark_negativ(self, score: float) -> bool:
        return score < 0.3

    def stark_positiv(self, score: float) -> bool:
        return score > 0.7

    def zeige_newsverlauf(self, epic: str) -> List[str]:
        """
        Platzhalter: Gibt zuletzt analysierte Nachrichten zurück.
        Später ersetzen durch echten Verlauf.
        """
        return ["Company beats expectations", "Stock upgrade by analyst"]

    def analysiere_nachricht(self, epic: str, text: str) -> Dict[str, str]:
        """
        Analysiert eine einzelne Nachricht und gibt das erkannte Sentiment zurück.
        """
        text = text.lower()
        for keyword in self.keywords["positive"]:
            if keyword in text:
                return {"sentiment": "bullish"}
        for keyword in self.keywords["negative"]:
            if keyword in text:
                return {"sentiment": "bearish"}
        return {"sentiment": "neutral"}
