import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

OUTPUT_DIR = "outputs"

os.makedirs(OUTPUT_DIR, exist_ok=True)

_PAGE_WIDTH, _PAGE_HEIGHT = letter
_MARGIN_X = 50
_MARGIN_TOP = 750
_MARGIN_BOTTOM = 50
_LINE_HEIGHT = 14
_FONT = "Helvetica"
_FONT_SIZE = 12


def generate_pdf(title: str, content: str) -> str:
    filename = title.replace(" ", "_") + ".pdf"
    path = os.path.join(OUTPUT_DIR, filename)

    c = canvas.Canvas(path, pagesize=letter)
    c.setFont(_FONT, _FONT_SIZE)

    y = _MARGIN_TOP
    for line in content.split("\n"):
        # Wrap long lines that exceed page width
        words = line.split(" ") if line else [""]
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip() if current else word
            if c.stringWidth(candidate, _FONT, _FONT_SIZE) > (_PAGE_WIDTH - _MARGIN_X * 2):
                c.drawString(_MARGIN_X, y, current)
                y -= _LINE_HEIGHT
                current = word
            else:
                current = candidate
        c.drawString(_MARGIN_X, y, current)
        y -= _LINE_HEIGHT

        if y < _MARGIN_BOTTOM:
            c.showPage()
            c.setFont(_FONT, _FONT_SIZE)
            y = _MARGIN_TOP

    c.save()
    return path