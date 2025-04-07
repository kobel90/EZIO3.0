# panel.py
class Panel:
    def __init__(self, content, title=None, expand=True):
        self.content = content
        self.title = title
        self.expand = expand

    def __str__(self):
        title_line = f"[ {self.title} ]" if self.title else ""
        panel_lines = [title_line, str(self.content)]
        return "\n".join(panel_lines)