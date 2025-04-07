from fastapi import FastAPI
import json

app = FastAPI()

@app.get("/")
def root():
    return {"status": "EZIO API läuft", "version": "1.0"}

@app.get("/get_log")
def get_log():
    try:
        with open("quellen_log.json") as f:
            return json.load(f)
    except Exception as e:
        return {"error": str(e)}

@app.get("/get_config")
def get_config():
    try:
        with open("config.json") as f:
            return json.load(f)
    except Exception as e:
        return {"error": str(e)}

@app.get("/get_status")
def get_status():
    return {
        "ezio_status": "läuft",
        "active_modules": ["TradingBot", "NewsKI", "SignalEngine"],
        "project": "EZIO3.0"
    }
