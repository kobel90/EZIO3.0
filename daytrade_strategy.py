from datetime import datetime, timedelta

def öffne_trade():
    print("Trade wurde geöffnet.")

class CapitalAllocator:
    def __init__(self, total_balance: float):
        self.total_balance = total_balance



    def allocate(self):
        margin_buffer = self.total_balance / 3  # 1/3 Margin-Puffer
        tradeable_capital = self.total_balance - margin_buffer
        longterm = tradeable_capital * 0.2
        daytrade = tradeable_capital * 0.8
        return {
            "total": self.total_balance,
            "buffer": margin_buffer,
            "longterm": longterm,
            "daytrade": daytrade
        }

class DaytradeStrategy:
    def __init__(self, max_duration_minutes=5, min_profit_percent=0.5, max_loss_percent=0.5):
        self.max_duration = timedelta(minutes=max_duration_minutes)
        self.min_profit = min_profit_percent / 100
        self.max_loss = max_loss_percent / 100

    def should_enter_trade(self, rsi, macd, signal):
        return (rsi < 50 and macd > signal) or (rsi > 50 and macd > signal)

    def should_exit_trade(self, entry_time, entry_price, current_price):
        now = datetime.now()
        time_in_trade = now - entry_time
        pnl_percent = (current_price - entry_price) / entry_price * 100

        if time_in_trade >= self.max_duration:
            return True, "⏱ Zeitlimit erreicht"
        elif pnl_percent >= self.min_profit * 100:
            return True, f"✅ Ziel erreicht: +{pnl_percent:.2f}%"
        elif pnl_percent <= -self.max_loss * 100:
            return True, f"🚨 Verlustgrenze erreicht: {pnl_percent:.2f}%"
        return False, "⌛ Noch halten"


# Beispielnutzung:
if __name__ == "__main__":
    allocator = CapitalAllocator(1500)
    print("Kapitalaufteilung:", allocator.allocate())

    strat = DaytradeStrategy()
    enter = strat.should_enter_trade(28, 1.1, 0.9)
    print("Trade starten?", enter)

    # Beispiel Exit nach 3 Minuten
    entry_time = datetime.now() - timedelta(minutes=3)
    exit_check, reason = strat.should_exit_trade(entry_time, 100, 100.6)
    print("Exit-Check:", reason)
