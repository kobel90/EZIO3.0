import tkinter as tk
from tkinter import ttk

class AggressionControlGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Aggression Control")

        # Der Switch ist direkt auf True (AGGRESSIV) gesetzt
        self.switch_var = tk.BooleanVar(value=True)

        self.switch = ttk.Checkbutton(
            self.root,
            text="Aggressiv",
            variable=self.switch_var,
            command=self.toggle_aggression
        )
        self.switch.pack(pady=10)

        self.status_label = ttk.Label(self.root, text=self.status_text())
        self.status_label.pack(pady=5)

    def attach_bot(self, bot):
        self.bot = bot

        # Übergibt den aktuellen Wert des Switches beim Start!
        initial_state = self.switch_var.get()
        self.bot.set_aggressiveness(initial_state)

        # Schaltet das Label auf den aktuellen Text
        self.status_label.config(text=self.status_text())

        # GUI starten
        self.root.mainloop()

    def toggle_aggression(self):
        new_state = self.switch_var.get()
        self.bot.set_aggressiveness(new_state)
        self.status_label.config(text=self.status_text())

    def status_text(self):
        return "Modus: AGGRESSIV" if self.switch_var.get() else "Modus: DEFENSIV"