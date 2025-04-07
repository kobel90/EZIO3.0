# utils/config_loader.py

import json

def load_config(path="config.json") -> dict:
    with open(path, "r") as f:
        return json.load(f)