import json
from typing import Dict

WHITELIST_PATH = "../whitelist_epics.json"

def load_whitelist() -> Dict[str, str]:
    try:
        with open(WHITELIST_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def update_whitelist(epic: str, name: str) -> None:
    whitelist = load_whitelist()
    if epic not in whitelist:
        print(f"🆕 Whitelist-Erweiterung: {epic} → {name}")
        whitelist[epic] = name
        with open(WHITELIST_PATH, "w", encoding="utf-8") as f:
            json.dump(whitelist, f, indent=2, ensure_ascii=False)