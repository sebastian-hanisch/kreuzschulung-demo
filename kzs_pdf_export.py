"""Auswertung als PDF (fpdf2, Kernschrift Helvetica: Umlaute gehen; Gedankenstrich, Euro-Zeichen, Emoji und das Minuszeichen U+2212 nicht).

Zwei aufeinanderfolgende multi_cell brauchen new_x=LMARGIN (sonst läuft die zweite aus der Seite)."""

from fpdf import FPDF

_REPLACE = {"–": "-", "—": "-", "−": "-", "≤": "<=", "≥": ">=", "→": "->", "↔": "<->", "…": "...", "€": "EUR", "·": ".", "±": "+/-", "×": "x",
            "²": "^2", "①": "1", "②": "2", "③": "3", "④": "4", "⑤": "5", "„": '"', "“": '"', "‚": "'", "‘": "'", "’": "'", "●": "*", "√": "Wurzel"}


def _clean(text):
    for a, b in _REPLACE.items():
        text = text.replace(a, b)
    return text.encode("latin-1", "replace").decode("latin-1")


def generate_pdf(title, summary_lines, rows, statement_lines, closing_lines=()):
    """Einstellung, Tabelle der Entwürfe (rows: Liste von Listen aus Textzellen, erste Zeile = Kopf), die Aussagen, Hinweise."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, _clean(title), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    for line in summary_lines:
        pdf.multi_cell(0, 5, _clean(line), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, _clean("Entwürfe: Anteil am Nutzen voller Flexibilität"), new_x="LMARGIN", new_y="NEXT")
    breiten = [44, 24, 30, 30, 30, 32]
    for k, row in enumerate(rows):
        pdf.set_font("Helvetica", "B" if k == 0 else "", 9)
        for w, cell in zip(breiten, row):
            pdf.cell(w, 5, _clean(str(cell)), border=0)
        pdf.ln(5)
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, _clean("Aussagen"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    for line in statement_lines:
        pdf.multi_cell(0, 5, _clean(line), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)
    if closing_lines:
        pdf.ln(2)
        pdf.set_font("Helvetica", "", 9)
        for line in closing_lines:
            pdf.multi_cell(0, 4.5, _clean(line), new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())
