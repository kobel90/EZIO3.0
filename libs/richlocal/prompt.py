class Prompt:
    @staticmethod
    def ask(text, choices=None, default=None):
        while True:
            eingabe = input(f"{text} ")
            if eingabe == "" and default is not None:
                return default
            if choices is None or eingabe in choices:
                return eingabe
            print(f"❌ Ungültige Eingabe. Erlaubt: {choices}")