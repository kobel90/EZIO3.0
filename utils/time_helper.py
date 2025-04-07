# utils/time_helper.py

def get_best_period_interval(days: int) -> tuple[str, str]:
    """
    Gibt das beste (period, interval)-Paar für yfinance zurück,
    basierend auf der gewünschten Anzahl Tage.
    """
    if days <= 5:
        return "7d", "1m"  # 1-Minuten-Daten für max. 7 Tage
    elif days <= 20:
        return "30d", "5m"
    elif days <= 60:
        return "60d", "15m"
    elif days <= 100:
        return "6mo", "1h"
    elif days <= 365:
        return "12mo", "1d"
    elif days <= 1500:
        return "5y", "1d"
    else:
        return "10y", "1wk"  # Wochenkerzen für lange Zeiträume
