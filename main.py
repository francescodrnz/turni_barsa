import pdfplumber
import os
import re
import glob
import json
from datetime import datetime
from fpdf import FPDF
import sys

DEBUG_MODE = False

def debug_print(*args, **kwargs):
    if DEBUG_MODE:
        print(*args, **kwargs)

def normalize_day_name(day_name):
    day_name = day_name.lower().strip()
    if day_name == 'mercoledì':
        return "mercoledi'"
    return day_name

def format_day_for_display(day_name):
    if day_name == "mercoledi'":
        return "mercoledì"
    return day_name

def get_raw_pdf_rows(file_path):
    """Ritorna una lista di tuple (indice_riga_tabella, contenuto_riga) per debug."""
    tables = read_pdf_tables(file_path)
    if not tables:
        return []
    
    raw_rows = []
    for table_idx, table in enumerate(tables):
        header_row_idx = -1
        # Cerchiamo l'header per dare un contesto agli indici
        for row_idx in range(min(3, len(table))):
            row = table[row_idx]
            if not row: continue
            for cell in row:
                if cell and re.search(r"([a-zàèéìòù']+)\s+(\d+)", str(cell), re.IGNORECASE):
                    header_row_idx = row_idx
                    break
            if header_row_idx != -1: break
        
        for row_idx, row in enumerate(table):
            # Calcoliamo l'indice relativo se abbiamo trovato l'header, altrimenti usiamo quello assoluto
            display_idx = row_idx - header_row_idx - 1 if header_row_idx != -1 else row_idx
            raw_rows.append({
                "Riga Assoluta": row_idx,
                "Indice Struttura": display_idx if row_idx > header_row_idx else f"Header ({row_idx})",
                "Contenuto": [str(c).replace('\n', ' ') if c else "" for c in row]
            })
    return raw_rows

def get_hardcoded_structure(json_path=None):
    """
    Carica la struttura da un file JSON se disponibile, altrimenti usa quella hardcoded.
    Il JSON ha la forma: {"0": ["Luogo", "HH:MM-HH:MM", ""], ...}
    """
    # Prova a caricare dal JSON
    search_paths = [json_path] if json_path else []
    search_paths += [
        os.path.join(os.path.dirname(__file__), "structure.json"),
        "structure.json"
    ]
    for path in search_paths:
        if path and os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                return {int(k): tuple(v) for k, v in raw.items()}
            except Exception as e:
                print(f"Avviso: impossibile caricare {path}: {e}")

    # Fallback hardcoded
    return {
        0: ("Giardini del Castello", "08:00-14:00", ""),
        1: ("Giardini del Castello", "08:00-14:00", ""),
        2: ("Giardini del Castello", "14:00-21:00", ""),
        3: ("Giardini del Castello", "16:00-22:00", ""),
        4: ("Giardini del Castello", "16:00-22:00", ""),
        5: ("Villa Bonelli", "09:00-13:00", ""),
        6: ("Villa Bonelli", "16:00-20:00", ""),
        7: ("Giardini v.le Giannone", "08:30-12:30", ""),
        8: ("Giardini v.le Giannone", "16:30-20:30", ""),
        9: ("Parco dell'Umanità", "09:00-11:00", ""),
        10: ("Parco dell'Umanità", "16:00-18:00", ""),
        11: ("Parco dell'Umanità", "16:00-20:00", ""),
        12: ("Giardini viale Manzoni-Via Da Vinci", "10:00-12:00", ""),
        13: ("Giardini viale Manzoni-Via Da Vinci", "16:15-20:15", ""),
        14: ("Giardini viale Manzoni-Via Da Vinci", "10:30-12:30", ""),
        15: ("Giardini viale Manzoni-Via Da Vinci", "17:15-20:15", ""),
        16: ("Paladisfida Borgia", "14:30-23:30", ""),
        17: ("Paladisfida Borgia", "08:15-13:15", ""),
        18: ("Paladisfida Borgia", "14:30-23:30", ""),
        19: ("Canne della Battaglia", "08:45-14:45", ""),
        20: ("Cantina della sfida", "09:00-13:00", ""),
        21: ("Cantina della sfida", "15:00-19:00", ""),
        22: ("Stadio Puttilli", "08:00-12:00", ""),
        23: ("Stadio Puttilli", "10:00-13:00", ""),
        24: ("Stadio Puttilli", "15:00-18:00", ""),
        25: ("Giardini via Chieffi", "10:00-13:00", ""),
        26: ("Giardini via Chieffi", "17:00-20:00", ""),
        27: ("Giardini Stadio Simeone", "10:00-13:00", ""),
        28: ("Giardini Stadio Simeone", "17:00-20:00", ""),
        29: ("Palazzo di Città", "06:00-12:00", ""),
        30: ("Palazzo di Città", "12:00-18:00", ""),
        31: ("Palazzo di Città", "18:00-24:00", ""),
        32: ("Palazzo di Città", "06:00-14:00", ""),
        33: ("Palazzo di Città", "14:00-22:00", ""),
        34: ("Cimitero", "07:30-12:30", ""),
        35: ("Cimitero", "15:00-19:00", ""),
        36: ("Cimitero", "06:30-13:30", ""),
        39: ("Sede Bar.S.A.", "00:00-06:20", ""),
        40: ("Sede Bar.S.A.", "06:40-13:00", ""),
        41: ("Sede Bar.S.A.", "11:40-18:00", ""),
        42: ("Sede Bar.S.A.", "18:00-24:00", ""),
        43: ("Sede Bar.S.A.", "00:00-08:00", ""),
        44: ("Sede Bar.S.A.", "08:00-16:00", ""),
        45: ("Sede Bar.S.A.", "16:00-24:00", ""),
        47: ("Distribuzione Prodotti", "15:00-20:00", ""),
        49: ("Riposo", "", ""),
        50: ("Riposo", "", ""),
        51: ("Riposo", "", ""),
        52: ("Riposo", "", ""),
        53: ("Riposo", "", ""),
        54: ("Riposo", "", ""),
        55: ("Riposo", "", ""),
        56: ("Riposo", "", ""),
        57: ("2° Riposo", "", ""),
        58: ("2° Riposo", "", ""),
        59: ("2° Riposo", "", ""),
        60: ("2° Riposo", "", ""),
        61: ("2° Riposo", "", ""),
        62: ("2° Riposo", "", ""),
        63: ("Ferie", "", ""),
        64: ("Ferie", "", ""),
        65: ("Ferie", "", ""),
        66: ("Ferie", "", ""),
        67: ("Ferie", "", ""),
        68: ("Malattia", "", ""),
        69: ("Malattia", "", ""),
        70: ("Malattia", "", ""),
        72: ("Permessi Vari", "", ""),
        73: ("Permessi Vari", "", ""),
        74: ("Permessi Vari", "", ""),
        75: ("Permessi Vari", "", ""),
        76: ("Permessi Vari", "", ""),
        77: ("Permessi Vari", "", ""),
    }

def structure_to_json_bytes(structure: dict) -> bytes:
    """Serializza la struttura (dict int->tuple) in JSON bytes scaricabili."""
    serializable = {str(k): list(v) for k, v in sorted(structure.items())}
    return json.dumps(serializable, ensure_ascii=False, indent=2).encode("utf-8")

def structure_from_json_bytes(data: bytes) -> dict:
    """Deserializza JSON bytes in struttura (dict int->tuple)."""
    raw = json.loads(data.decode("utf-8"))
    return {int(k): tuple(v) for k, v in raw.items()}

def read_pdf_tables(file_path):
    try:
        with pdfplumber.open(file_path) as pdf:
            all_tables = []
            for page in pdf.pages:
                tables = page.extract_tables()
                all_tables.extend(tables)
            return all_tables
    except Exception as e:
        print(f"Errore nella lettura del PDF: {str(e)}")
        return None

def parse_pdf(file_path):
    return read_pdf_tables(file_path)

def extract_days_from_header(tables):
    days = []
    for table in tables:
        if not table:
            continue
        for row_idx in range(min(3, len(table))):
            row = table[row_idx]
            if not row:
                continue
            debug_print(f"Debug: Analizzando header riga {row_idx}: {row}")
            for cell in row:
                if cell:
                    cell_text = str(cell).strip()
                    match = re.match(r"([a-zàèéìòù']+)\s+(\d+)", cell_text, re.IGNORECASE)
                    if match:
                        giorno = normalize_day_name(match.group(1))
                        if giorno in ['lunedì', 'martedì', "mercoledi'", 'giovedì', 'venerdì', 'sabato', 'domenica']:
                            days.append((giorno, match.group(2)))
                            debug_print(f"Debug: Trovato giorno: {giorno} {match.group(2)}")
            if days:
                break
        if days:
            break
    debug_print(f"Debug: Giorni estratti: {days}")
    return days

def extract_shifts_for_person_hardcoded(tables, surname, structure=None):
    """
    Estrae i turni per il cognome specificato.
    structure: dict opzionale {int: (location, time_slot, notes)}.
               Se None, carica da get_hardcoded_structure().
    """
    if not tables:
        return []

    days = extract_days_from_header(tables)
    if not days:
        print("Errore: Non è stato possibile trovare i giorni nelle tabelle")
        return []

    if structure is None:
        structure = get_hardcoded_structure()

    shifts = []
    days_with_shifts = set()

    debug_print(f"\nCercando turni per: {surname}")

    for table in tables:
        if not table:
            continue

        debug_print(f"\nDebug: Processando tabella con {len(table)} righe")

        day_columns = {}
        header_row_idx = -1

        for row_idx in range(min(3, len(table))):
            row = table[row_idx]
            if not row:
                continue
            temp_day_columns = {}
            for col_idx, cell in enumerate(row):
                if cell:
                    cell_text = str(cell).strip()
                    match = re.match(r"([a-zàèéìòù']+)\s+(\d+)", cell_text, re.IGNORECASE)
                    if match:
                        giorno = normalize_day_name(match.group(1))
                        numero = match.group(2)
                        if giorno in ['lunedì', 'martedì', "mercoledi'", 'giovedì', 'venerdì', 'sabato', 'domenica']:
                            temp_day_columns[col_idx] = (giorno, numero)
            if temp_day_columns:
                day_columns = temp_day_columns
                header_row_idx = row_idx
                break

        if not day_columns:
            continue

        debug_print(f"Debug: Header trovato nella riga {header_row_idx}")
        debug_print(f"Debug: Colonne giorni: {day_columns}")

        for row_idx in range(header_row_idx + 1, len(table)):
            row = table[row_idx]
            if not row or all(cell is None or str(cell).strip() == '' for cell in row):
                continue

            structure_idx = row_idx - header_row_idx - 1
            debug_print(f"\nDebug: Riga {row_idx} (struttura idx {structure_idx}): {[str(cell)[:30] if cell else None for cell in row[:5]]}")

            if structure_idx in structure and structure[structure_idx] is not None:
                location, time_slot, notes = structure[structure_idx]
            else:
                debug_print(f"Debug: Struttura non definita per riga {structure_idx}, uso fallback Riposo")
                location = "Riposo"
                time_slot = ""
                notes = ""

            for col_idx, cell in enumerate(row):
                if cell and surname.lower() in str(cell).lower():
                    if col_idx in day_columns:
                        day_name, day_number = day_columns[col_idx]
                        debug_print(f"Debug: Trovato '{surname}' in {day_name} {day_number} (colonna {col_idx})")
                        days_with_shifts.add(day_name)

                        final_location = location if location else "Turno"
                        final_time = time_slot if time_slot else ""

                        if "CHIUSO" in final_location.upper() or "CHIUSA" in final_location.upper():
                            shifts.append((day_name, day_number, "Riposo - " + final_location, "", ""))
                        elif "riposo" in final_location.lower() or "ferie" in final_location.lower():
                            shifts.append((day_name, day_number, final_location, "", ""))
                        else:
                            shifts.append((day_name, day_number, final_location, final_time, ""))

                        debug_print(f"Debug: Aggiunto turno: {day_name} {day_number}, {final_location}, {final_time}")

    for day_name, day_number in days:
        if day_name not in days_with_shifts:
            shifts.append((day_name, day_number, "Riposo", "", ""))

    debug_print(f"\nDebug: Totale turni trovati: {len(shifts)}")
    return shifts

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

    pdf.set_font("Arial", size=12)
    pdf.set_fill_color(200, 200, 200)

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
        header += " {'Pulizia bagni':<12}"
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

    surname = input("Inserisci il cognome: ").strip()
    tables = read_pdf_tables(pdf_path)
    if tables is None:
        return

    shifts = extract_shifts_for_person_hardcoded(tables, surname)
    if not shifts:
        print(f"\nNessun turno trovato per {surname}")
        return

    shifts_sorted = sort_days(shifts)
    print_shifts(shifts_sorted)

    if input("\nSono necessarie modifiche ai turni? (s/n): ").strip().lower() in ['s', 'si', 'sì', 'y', 'yes']:
        from main import modify_shifts  # CLI only
        shifts_sorted = modify_shifts(shifts_sorted)

    write_shifts_to_pdf(shifts_sorted, pdf_path, surname)
    input("Premi Invio per uscire...")

if __name__ == "__main__":
    main()
