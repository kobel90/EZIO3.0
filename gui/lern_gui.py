# gui/lern_gui.py

import tkinter as tk
from tkinter import filedialog, messagebox
from lernzentrum.lern_interface import LernInterface
from trading_ki import TradingKI

class LernGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("📚 EZIO – Lernzentrum")
        self.root.geometry("520x350")

        self.interface = LernInterface()
        self.ki = TradingKI()

        # 📘 Titel
        tk.Label(self.root, text="🔍 EZIO Wissens-Upload", font=("Arial", 14, "bold")).pack(pady=10)

        # 🔗 Webseite
        tk.Label(self.root, text="🌐 URL eingeben:").pack()
        self.url_entry = tk.Entry(self.root, width=55)
        self.url_entry.pack(pady=2)
        tk.Button(self.root, text="🔍 Von Webseite lernen", command=self.lerne_von_webseite).pack(pady=5)

        # 📂 Datei
        tk.Button(self.root, text="📁 Datei auswählen (.txt/.html)", command=self.lerne_aus_datei).pack(pady=5)

        # 🗂️ Ordner
        tk.Button(self.root, text="🗂️ Ordner mit Texten einlesen", command=self.autodurchlauf).pack(pady=5)

        # 🧠 Lernstatus
        self.status = tk.Label(self.root, text="", fg="green")
        self.status.pack(pady=15)

    def lerne_von_webseite(self):
        url = self.url_entry.get().strip()
        if url:
            text = self.interface.lade_webseite(url)
            if text:
                self.ki.lerne_aus_text(text, quelle=url)
                self.status.config(text="✅ Webseite analysiert & gespeichert")
        else:
            messagebox.showerror("Fehler", "Bitte URL eingeben.")

    def lerne_aus_datei(self):
        pfad = filedialog.askopenfilename(filetypes=[("Textdateien", "*.txt *.html")])
        if pfad:
            self.ki.lerne_aus_datei(pfad)
            self.status.config(text=f"📄 Datei verarbeitet: {pfad}")

    def autodurchlauf(self):
        self.interface.autodurchlauf(self.ki)
        self.status.config(text="📚 Auto-Durchlauf abgeschlossen")

    def starten(self):
        self.root.mainloop()

# Direkt starten
if __name__ == "__main__":
    gui = LernGUI()
    gui.starten()