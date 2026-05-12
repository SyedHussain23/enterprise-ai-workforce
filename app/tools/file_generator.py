import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

OUTPUT_DIR = "outputs"

os.makedirs(OUTPUT_DIR, exist_ok=True)


def generate_pdf(title: str, content: str):

    filename = title.replace(" ", "_") + ".pdf"

    path = os.path.join(OUTPUT_DIR, filename)

    c = canvas.Canvas(path, pagesize=letter)

    text = c.beginText(50, 750)
    text.setFont("Helvetica", 12)

    for line in content.split("\n"):
        text.textLine(line)

    c.drawText(text)

    c.save()

    return path