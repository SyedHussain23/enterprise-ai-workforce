from app.tools.file_generator import generate_pdf


def generate_report(title: str, content: str):

    path = generate_pdf(title, content)

    return {
        "message": f"Report generated: {path}",
        "file": path
    }