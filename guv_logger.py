import csv
from datetime import datetime

def log_guv_to_csv(balance, comment="", logfile="guv_log.csv"):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(logfile, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([timestamp, round(balance, 2), comment])
        print(f"[Logger] Trade gespeichert: {timestamp} | {round(balance, 2)} | {comment}")