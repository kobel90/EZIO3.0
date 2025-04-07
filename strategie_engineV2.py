import os
from datetime import datetime
from typing import List, Dict, Any, Optional
import pandas as pd
import random

def calculate_sma(epic: str, period: int = 20, prices: Optional[List[float]] = None) -> Optional[float]:
    if not prices or len(prices) < period:
        print(f"⚠️ Nicht genügend Daten für SMA von {epic} (mind. {period} benötigt)")
        return None
    try:
        series = pd.Series(prices)
        sma_series = series.rolling(window=period).mean()
        if sma_series.empty:
            print(f"⚠️ Leere SMA-Serie bei {epic}")
            return None
        return sma_series.iloc[-1]
    except Exception as e:
        print(f"❌ Fehler bei SMA-Berechnung für {epic}: {e}")
        return None

def berechne_macd(preise: List[float], kurz=12, lang=26, signal=9):
    if len(preise) < lang:
        return None, None
    kurz_ema = pd.Series(preise).ewm(span=kurz, adjust=False).mean()
    lang_ema = pd.Series(preise).ewm(span=lang, adjust=False).mean()
    macd_line = kurz_ema - lang_ema
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line.iloc[-1], signal_line.iloc[-1]

def ist_einstieg_geeignet(data: Dict[str, Any]) -> bool:
    punkte = 0
    print(f"📊 Analyse für {data.get('name', 'Unbekannt')}")
    print(f"➡️ Eingabedaten: {data}")

    preise = data.get("preise", [])
    macd, signal = berechne_macd(preise)

    if macd is not None and signal is not None and macd > signal:
        punkte += 1
        print("✅ Punkt für MACD-Crossover")
    else:
        print("❌ Kein Punkt: MACD kein Crossover")

    if data.get("rsi", 100) < 45:
        punkte += 1
        print("✅ Punkt für RSI < 45")
    else:
        print("❌ Kein Punkt: RSI zu hoch")

    if data.get("ema50", 0) > data.get("ema200", 9999):
        punkte += 1
        print("✅ Punkt für EMA50 > EMA200")
    else:
        print("❌ Kein Punkt: EMA50 nicht über EMA200")

    if data.get("volumen", 0) > data.get("volumen_schnitt", 1) * 1.2:
        punkte += 1
        print("✅ Punkt für Volumenspike")
    else:
        print("❌ Kein Punkt: Volumen zu niedrig")

    if abs(data.get("price", 0) - data.get("support", -999)) < 0.1:
        punkte += 1
        print("✅ Punkt für Nähe zu Support")
    else:
        print("❌ Kein Punkt: Preis nicht nahe Support")

    if abs(data.get("price", 0) - data.get("resistance", -999)) < 0.1:
        punkte += 1
        print("✅ Punkt für Nähe zu Resistance")
    else:
        print("❌ Kein Punkt: Preis nicht nahe Resistance")

    if any(abs(data.get("price", 0) - level) < 0.3 for level in data.get("fibonacci", [])):
        punkte += 1
        print("✅ Punkt für Fibonacci-Level-Treffer")
    else:
        print("❌ Kein Punkt: Kein Fibonacci-Level nahe Preis")

    if "force_trade" in lade_strategie_dateien():
        punkte += 3
        print("⚠️ FORCED TRADE durch Keyword erkannt!")

    print(f"➡️ Vergebene Punkte: {punkte}/7")
    return punkte >= 2

def berechne_volatilitaet_preise(prices: List[float]) -> float:
    if not prices or len(prices) < 2:
        return 0.0
    returns = [abs((prices[i] - prices[i - 1]) / prices[i - 1]) for i in range(1, len(prices))]
    return (sum(returns) / len(returns)) * 100

def berechne_volatilitaet_kerze(candles: list, aktueller_preis: float) -> float:
    if not candles or aktueller_preis == 0:
        return 0.01
    high_wert = max(c["high"] for c in candles)
    low_wert = min(c["low"] for c in candles)
    return round((high_wert - low_wert) / aktueller_preis, 4)

def lade_strategie_dateien(pfad="strategien.txt") -> List[str]:
    if not os.path.exists(pfad):
        return []
    with open(pfad, "r") as f:
        return [zeile.strip().lower() for zeile in f.readlines()]

def schaetze_trade_dauer(data: Dict[str, Any]) -> int:
    volatilitaet = data.get("volatilität", 0.01)
    volumen = data.get("volumen", 0)
    volumen_schnitt = data.get("volumen_schnitt", 1)
    spike_faktor = volumen / volumen_schnitt if volumen_schnitt > 0 else 1

    if volatilitaet < 0.005:
        basis = 30
    elif volatilitaet > 0.02:
        basis = 5
    else:
        basis = 15

    dauer = basis / spike_faktor
    return max(2, min(int(dauer), 60))


def ermittle_richtung(data: Dict[str, Any]) -> str:
    preise = data.get("preise", [])
    preis = data.get("price", 0)
    ema200 = data.get("ema200", None)

    if ema200 is not None:
        if preis > ema200:
            print("📈 Richtung = BUY (Preis über EMA200)")
            return "BUY"
        else:
            print("📉 Richtung = SELL (Preis unter EMA200)")
            return "SELL"

    # Fallback: letzter Preisvergleich
    if len(preise) >= 2:
        if preise[-1] > preise[-2]:
            print("📈 Richtung = BUY (Preis steigt)")
            return "BUY"
        elif preise[-1] < preise[-2]:
            print("📉 Richtung = SELL (Preis fällt)")
            return "SELL"

    print("⏸️ Richtung = HOLD (kein Trend erkennbar)")
    return "HOLD"

def erstelle_signal(data: Dict[str, Any], api=None) -> Optional[Dict[str, Any]]:
    epic = data.get("epic")
    price = data.get("price")
    direction = ermittle_richtung(data)
    dauer = schaetze_trade_dauer(data)
    size = api.berechne_trade_groesse(epic) if api else 1.0

    return {
        "epic": epic,
        "price": price,
        "direction": direction,
        "size": size,
        "dauer": dauer,
        "zeit": datetime.now().isoformat()
    }

def berechne_zielbereiche() -> dict:
    # Take-Profit zufällig zwischen 10 % und 15 %
    tp = round(random.uniform(0.10, 0.15), 3)
    # Stop-Loss zufällig zwischen -7 % und -10 %
    sl = round(random.uniform(-0.10, -0.07), 3)

    return {
        "take_profit_pct": tp,
        "stop_loss_pct": abs(sl)  # später positiv speichern für Vergleich
    }