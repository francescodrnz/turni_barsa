import pdfplumber
import os
import re
import glob
from datetime import datetime
from fpdf import FPDF
import sys

DEBUG_MODE = False

def debug_print(*args, **kwargs):
    if DEBUG_MODE:
        print(*args, **kwargs)

def normalize_day_name(day_name):
    # Il PDF scrive i giorni a volte con l'accento (lunedì) a volte con l'apostrofo (lunedi')
    day_name = day_name.lower().strip().replace('’', "'")
    day_name = re.sub(r"(i'|ì)$", "ì", day_name)
    if day_name == 'mercoledì':
        return "mercoledi'"
    return day_name

def format_day_for_display(day_name):
    if day_name == "mercoledi'":
        return "mercoledì"
    return day_name

DAY_NAMES = ['lunedì', 'martedì', "mercoledi'", 'giovedì', 'venerdì', 'sabato', 'domenica']
DAY_HEADER = re.compile(r"([a-zàèéìòù'’]+)\s+(\d+)", re.IGNORECASE)
TIME_RANGE = re.compile(r"(\d{1,2})[:,.]+(\d{2})\s*[-/]?\s*(\d{1,2})[:,.]+(\d{2})")

# Etichette di colonna 0 che non sono luoghi ma dicono quando vale il blocco sopra
# ("domenica", "sabato, domenica e fest. Feriali", "dal Lun. al Sabato").
QUALIFIER_WORDS = {'dal', 'al', 'e', 'ed', 'solo', 'fest', 'festivi', 'festivo', 'feriali', 'feriale'}

# Luoghi che sono stati della persona, non posti di lavoro: non hanno orario.
STATUS_LOCATIONS = ('riposo', 'ferie', 'malattia', 'assente', 'permess', 'infortunio', 'non lavora')

MIN_LOCATIONS = 5


def is_qualifier(label):
    words = re.findall(r"[a-zàèéìòù]+", label.lower())
    if not words:
        return False
    for w in words:
        if w in QUALIFIER_WORDS:
            continue
        if len(w) >= 3 and any(d.startswith(w) or w.startswith(d.rstrip("ì'")) for d in DAY_NAMES):
            continue
        return False
    return True


def normalize_time(text):
    """'12,00-18,00', '09:0011:00', '15::00-21:00', '14:30-23:30 Rossi' -> 'HH:MM-HH:MM'."""
    m = TIME_RANGE.search(text or '')
    if not m:
        return ''
    return f"{int(m[1]):02d}:{m[2]}-{int(m[3]):02d}:{m[4]}"


def _day_columns(row):
    cols = {}
    for col_idx, cell in enumerate(row):
        if cell:
            match = DAY_HEADER.match(str(cell).strip())
            if match:
                giorno = normalize_day_name(match.group(1))
                if giorno in DAY_NAMES:
                    cols[col_idx] = (giorno, match.group(2))
    return cols


def _is_dark(color):
    if color is None:
        return False
    if isinstance(color, (int, float)):
        color = (color,)
    return all(isinstance(c, (int, float)) and c <= 0.5 for c in color)


def _segments(page, row_tops, xa, xb):
    """
    Divide le righe in blocchi: un blocco nuovo comincia dove, fra xa e xb, c'è
    un bordo orizzontale. Excel li disegna solo fra un blocco e l'altro.
    """
    borders = [
        o['top'] for o in page.rects + page.lines
        if o['height'] < 3 and o['x0'] < xa + 5 and o['x1'] > xb - 5
        and _is_dark(o.get('non_stroking_color') if o['object_type'] == 'rect' else o.get('stroking_color'))
    ]
    segments = []
    for i, top in enumerate(row_tops[:-1]):
        if not segments or any(abs(y - top) < 2 for y in borders):
            segments.append([i, i])
        else:
            segments[-1][1] = i
    return segments


def _text_in(page, x0, top, x1, bottom):
    """Testo dei caratteri con il centro nel riquadro: niente testo che sconfina dal blocco vicino."""
    chars = [c for c in page.chars
             if x0 <= (c['x0'] + c['x1']) / 2 <= x1 and top <= (c['top'] + c['bottom']) / 2 <= bottom]
    return ' '.join(pdfplumber.utils.extract_text(chars).split()) if chars else ''


def read_shift_table(file_path):
    """
    Legge la tabella dei turni e assegna a ogni riga luogo e orario.
    Ritorna {"days": {col: (giorno, numero)}, "rows": [{"riga", "etichetta",
    "luogo", "orario", "celle"}]}.
    Il luogo è l'etichetta del blocco in colonna 0 (o del blocco sopra, se
    l'etichetta è un qualificatore come "domenica"); l'orario è la cella della
    colonna 1, anche quando copre più righe.
    Solleva ValueError se il PDF non ha testo o se la tabella non ha la forma attesa.
    """
    try:
        pdf = pdfplumber.open(file_path)
    except Exception as e:
        raise ValueError(f"Impossibile leggere il PDF: {e}") from e
    with pdf:
        if not any(page.chars for page in pdf.pages):
            raise ValueError("Il PDF è una scansione senza testo: non si può leggere.")

        best = None
        for page in pdf.pages:
            for table in page.find_tables():
                data = table.extract()
                for header_idx in range(min(3, len(data))):
                    days = _day_columns(data[header_idx])
                    if days:
                        if best is None or len(data) > len(best[2]):
                            best = (page, table, data, header_idx, days)
                        break
        if best is None:
            raise ValueError("Non trovo la tabella dei turni con l'intestazione dei giorni.")
        page, table, data, header_idx, days = best

        x0, x1, x2 = (col.bbox[0] for col in table.columns[:3])
        row_tops = [row.bbox[1] for row in table.rows] + [table.bbox[3]]
        time_cell = {}
        for a, b in _segments(page, row_tops, x1, x2):
            text = _text_in(page, x1, row_tops[a], x2, row_tops[b + 1])
            for i in range(a, b + 1):
                time_cell[i] = text

        rows = []
        location = None
        for a, b in _segments(page, row_tops, x0, x1):
            label = _text_in(page, x0, row_tops[a], x1, row_tops[b + 1])
            if label and not is_qualifier(label):
                location = label
            elif not label and not any(normalize_time(time_cell[i]) for i in range(a, b + 1)):
                location = None  # riga vuota di separazione fra le sezioni
            for i in range(a, b + 1):
                cells = [str(c).strip() if c else '' for c in data[i]]
                is_header = i <= header_idx or cells[1].lower() == 'turno'
                rows.append({
                    "riga": i,
                    "etichetta": label,
                    "luogo": None if is_header else location,
                    "orario": '' if is_header else normalize_time(time_cell[i]),
                    "celle": cells,
                    "header": is_header,
                })

    if len({r["luogo"] for r in rows if r["luogo"]}) < MIN_LOCATIONS:
        raise ValueError("Struttura del PDF non riconosciuta (bordi diversi dal solito?): "
                         "controlla la tabella a mano.")
    return {"days": days, "rows": rows}


def table_debug_rows(table):
    """Una riga per riga del PDF, con luogo e orario assegnati: per la vista di controllo."""
    return [{
        "Riga": r["riga"],
        "Etichetta blocco": r["etichetta"],
        "Luogo": r["luogo"] or "",
        "Orario": r["orario"],
        "Contenuto": " | ".join(c.replace('\n', ' ') for c in r["celle"][2:] if c),
    } for r in table["rows"]]


def is_status_location(location):
    return any(s in location.lower() for s in STATUS_LOCATIONS)


def extract_shifts_for_person(table, surname):
    """
    Estrae i turni per il cognome specificato da una tabella di read_shift_table.
    Ritorna (turni, avvisi): gli avvisi segnalano righe col cognome senza luogo
    o senza orario, da controllare a mano.
    """
    days = table["days"]
    shifts = []
    warnings = []
    days_with_shifts = set()

    for row in table["rows"]:
        if row["header"]:
            continue
        for col_idx, cell in enumerate(row["celle"]):
            if col_idx not in days or not cell or surname.lower() not in cell.lower():
                continue
            day_name, day_number = days[col_idx]
            days_with_shifts.add(day_name)
            debug_print(f"Debug: '{surname}' in {day_name} {day_number}, riga {row['riga']}: {row['luogo']} {row['orario']}")

            location = row["luogo"]
            final_time = row["orario"]
            time_override = normalize_time(cell)
            if time_override:
                final_time = time_override

            if not location:
                warnings.append(f"{format_day_for_display(day_name)} {day_number}: riga {row['riga']} del PDF "
                                f"senza luogo riconosciuto, controlla a mano.")
                shifts.append((day_name, day_number, "Luogo non riconosciuto", final_time, ""))
            elif "CHIUSO" in location.upper() or "CHIUSA" in location.upper():
                shifts.append((day_name, day_number, "Riposo - " + location, "", ""))
            elif is_status_location(location):
                shifts.append((day_name, day_number, location, "", ""))
            else:
                if not final_time:
                    warnings.append(f"{format_day_for_display(day_name)} {day_number}: {location}, "
                                    f"orario non trovato nella riga {row['riga']} del PDF.")
                shifts.append((day_name, day_number, location, final_time, ""))

    if not days_with_shifts:
        warnings.append(f"{surname} non compare nel PDF.")
    for day_name, day_number in days.values():
        if day_name not in days_with_shifts:
            shifts.append((day_name, day_number, "Riposo", "", ""))

    debug_print(f"\nDebug: Totale turni trovati: {len(shifts)}")
    return shifts, warnings


def has_giardini_castello(shifts):
    for shift in shifts:
        if "giardini del castello" in shift[2].lower():
            return True
    return False

def sort_days(shifts):
    day_order = {
        'lunedì': 1, 'martedì': 2, "mercoledi'": 3,
        'giovedì': 4, 'venerdì': 5, 'sabato': 6, 'domenica': 7
    }

    def get_day_number(shift):
        return day_order.get(normalize_day_name(shift[0]), 8)

    def get_time(shift):
        time_str = shift[3]
        if time_str:
            try:
                return datetime.strptime(time_str.split('-')[0].strip(), "%H:%M")
            except (ValueError, IndexError):
                return datetime.max
        return datetime.max

    return sorted(shifts, key=lambda s: (get_day_number(s), get_time(s)))

def write_shifts_to_pdf(shifts, input_filename, surname):
    shifts = sort_days(shifts)

    match = re.search(r"DAL.*\.pdf", input_filename, re.IGNORECASE)
    output_filename = f"Turni {surname} " + match.group(0).lower() if match else f"Turni {surname}.pdf"

    has_bagni = has_giardini_castello(shifts)

    if has_bagni:
        updated_shifts = []
        for shift in shifts:
            if len(shift) < 5:
                pulizia = "No" if "giardini del castello" in shift[2].lower() else ""
                updated_shifts.append(shift + (pulizia,))
            else:
                pulizia_value = shift[4]
                if "giardini del castello" in shift[2].lower() and not pulizia_value:
                    updated_shifts.append(shift[:4] + ("No",))
                else:
                    updated_shifts.append(shift)
        shifts = updated_shifts

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Arial", "B", size=17)
    pdf.cell(200, 10, txt=f"Turni di lavoro {surname}", ln=True, align='C')
    pdf.ln(10)

    # Calculate total table width to center it
    if has_bagni:
        table_width = 25 + 10 + 80 + 40 + 30 # = 185
    else:
        table_width = 30 + 15 + 85 + 60 # = 190
    
    page_width = 210 # A4 width in mm
    x_offset = (page_width - table_width) / 2

    pdf.set_font("Arial", size=12)
    pdf.set_fill_color(200, 200, 200)

    pdf.set_x(x_offset)
    if has_bagni:
        pdf.cell(25, 10, 'Giorno', border='LTB', align='R', fill=True)
        pdf.cell(10, 10, ' ', border='RTB', align='C', fill=True)
        pdf.cell(80, 10, 'Luogo', border=1, align='C', fill=True)
        pdf.cell(40, 10, 'Orario', border=1, align='C', fill=True)
        pdf.cell(30, 10, 'Pulizia bagni', border=1, align='C', fill=True)
    else:
        pdf.cell(30, 10, 'Giorno', border='LTB', align='R', fill=True)
        pdf.cell(15, 10, ' ', border='RTB', align='C', fill=True)
        pdf.cell(85, 10, 'Luogo', border=1, align='C', fill=True)
        pdf.cell(60, 10, 'Orario', border=1, align='C', fill=True)
    pdf.ln()

    for shift in shifts:
        day, day_number, location, time = shift[:4]
        pulizia_bagni = shift[4] if len(shift) > 4 else ""
        day_display = format_day_for_display(day)

        pdf.set_x(x_offset)
        if has_bagni:
            pdf.cell(25, 10, day_display, border='LTB', align='R')
            pdf.cell(10, 10, day_number, border='RTB', align='L')
            pdf.cell(80, 10, location[:40], border=1, align='C')
            pdf.cell(40, 10, time, border=1, align='C')
            pdf.cell(30, 10, pulizia_bagni, border=1, align='C')
        else:
            pdf.cell(30, 10, day_display, border='LTB', align='R')
            pdf.cell(15, 10, day_number, border='RTB', align='L')
            pdf.cell(85, 10, location[:44], border=1, align='C')
            pdf.cell(60, 10, time, border=1, align='C')
        pdf.ln()

    pdf.output(output_filename)
    print(f"File '{output_filename}' creato con successo!")
    return output_filename

# ── CLI ──────────────────────────────────────────────────────────────────────

def print_shifts(shifts):
    has_bagni = has_giardini_castello(shifts)
    sep = "-" * (100 if has_bagni else 80)
    print(f"\nTurni attuali:\n{sep}")
    header = f"{'N.':<3} {'Giorno':<12} {'Data':<6} {'Luogo':<35} {'Orario':<15}"
    if has_bagni:
        header += f" {'Pulizia bagni':<12}"
    print(header)
    print(sep)
    for i, shift in enumerate(shifts, 1):
        day, day_number, location, time = shift[:4]
        pulizia_bagni = shift[4] if len(shift) > 4 else ""
        day_display = format_day_for_display(day)
        row = f"{i:<3} {day_display:<12} {day_number:<6} {location:<35} {time:<15}"
        if has_bagni:
            row += f" {pulizia_bagni:<12}"
        print(row)
    print(sep)

def find_pdf_file():
    pdf_files = []
    for file in glob.glob(os.path.join(os.getcwd(), "*")):
        if file.lower().endswith('.pdf') and os.path.basename(file).lower().startswith('servizio custodia'):
            pdf_files.append(file)
    return pdf_files

def main():
    global DEBUG_MODE
    DEBUG_MODE = input("Vuoi attivare la modalità debug? (s/n): ").strip().lower() in ['s', 'si', 'sì', 'y', 'yes']
    if DEBUG_MODE:
        print("Modalità debug attivata.")
    print()

    pdf_files = find_pdf_file()
    pdf_path = None

    if pdf_files:
        if len(pdf_files) == 1:
            filename = os.path.basename(pdf_files[0])
            if input(f"Trovato file: {filename}\nConfermi? (s/n): ").strip().lower() in ['s', 'si', 'sì', 'y', 'yes']:
                pdf_path = pdf_files[0]
        else:
            for i, file in enumerate(pdf_files, 1):
                print(f"{i}. {os.path.basename(file)}")
            while pdf_path is None:
                try:
                    scelta = int(input("Quale file vuoi processare? (numero): ")) - 1
                    if 0 <= scelta < len(pdf_files):
                        pdf_path = pdf_files[scelta]
                except ValueError:
                    pass

    if pdf_path is None:
        pdf_path = input("Inserisci il nome del file PDF (inclusa estensione .pdf): ")

    surname = ""
    while len(surname) < 3:
        surname = input("Inserisci il cognome: ").strip()
    try:
        table = read_shift_table(pdf_path)
    except ValueError as e:
        print(f"Errore: {e}")
        return

    shifts, warnings = extract_shifts_for_person(table, surname)
    for w in warnings:
        print(f"ATTENZIONE: {w}")

    shifts_sorted = sort_days(shifts)
    print_shifts(shifts_sorted)

    write_shifts_to_pdf(shifts_sorted, pdf_path, surname)
    input("Premi Invio per uscire...")

if __name__ == "__main__":
    main()
