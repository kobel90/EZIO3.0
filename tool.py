from typing import List

def schaetze_trade_dauer(prices: List[float]) -> int:
    """
    Schätzt die durchschnittliche Dauer einer typischen Preisbewegung (Tief zu Hoch oder umgekehrt) in Minuten.
    """
    if not prices or len(prices) < 10:
        return 10  # Fallback-Wert

    bewegungen = []
    last_extrem = prices[0]
    last_index = 0
    richtung = None  # "hoch" oder "runter"

    for i in range(1, len(prices)):
        delta = prices[i] - prices[i - 1]
        neue_richtung = "hoch" if delta > 0 else "runter" if delta < 0 else richtung

        if richtung and neue_richtung != richtung:
            dauer = i - last_index
            bewegungen.append(dauer)
            last_extrem = prices[i]
            last_index = i

        richtung = neue_richtung

    if not bewegungen:
        return 10

    durchschnitt = sum(bewegungen) / len(bewegungen)
    return int(durchschnitt)