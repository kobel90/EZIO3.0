import json
import os
from datetime import datetime
from typing import Dict, Any

class SLTPManager:
    def __init__(self, config_path="sl_tp_config.json", history_path="sl_tp_history.json"):
        self.config_path = config_path
        self.history_path = history_path
        self.data = self.load_config()

    def load_config(self) -> Dict[str, Any]:
        if os.path.exists(self.config_path):
            with open(self.config_path, "r") as f:
                return json.load(f)
        else:
            return {}

    def save_config(self) -> None:
        with open(self.config_path, "w") as f:
            json.dump(self.data, f, indent=2)

    def log_change(self, asset: str, sl_old: float, sl_new: float, tp_old: float, tp_new: float) -> None:
        history_entry = {
            "timestamp": datetime.now().isoformat(),
            "asset": asset,
            "old_values": {"stop_loss": sl_old, "take_profit": tp_old},
            "new_values": {"stop_loss": sl_new, "take_profit": tp_new}
        }
        if os.path.exists(self.history_path):
            with open(self.history_path, "r") as f:
                history = json.load(f)
        else:
            history = []
        history.append(history_entry)
        with open(self.history_path, "w") as f:
            json.dump(history, f, indent=2)

    def update_sl_tp(self, asset: str, sl: float, tp: float) -> None:
        old = self.data.get(asset, self.data.get("default", {}))
        sl_old = old.get("stop_loss_percent", 0)
        tp_old = old.get("take_profit_percent", 0)

        if sl != sl_old or tp != tp_old:
            self.data[asset] = {
                "stop_loss_percent": sl,
                "take_profit_percent": tp
            }
            self.save_config()
            self.log_change(asset, sl_old, sl, tp_old, tp)

    def get_params(self, epic: str) -> dict:
        params = self.data.get(epic, self.data.get("default", {
            "stop_loss_percent": 0.03,
            "take_profit_percent": 0.05
        }))

        # Optionaler Debug-Ausdruck
        print(f"⚙️ SL/TP-Werte für {epic} → SL: {params['stop_loss_percent']}, TP: {params['take_profit_percent']}")
        return params