# text.py
class Text(str):
    def __init__(self, value, style=None):
        self.value = value
        self.style = style

    def __new__(cls, content, style=None):
        obj = str.__new__(cls, content)
        obj.style = style
        return obj

    def __str__(self):
        return self.value