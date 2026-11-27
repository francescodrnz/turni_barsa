import pdfplumber
import os
import re
import glob
from datetime import date, datetime, timedelta
from fpdf import FPDF
import sys
import json
import unicodedata

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
MONTH_NAMES = ['gennaio', 'febbraio', 'marzo', 'aprile', 'maggio', 'giugno', 'luglio',
               'agosto', 'settembre', 'ottobre', 'novembre', 'dicembre']
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


def _color(rect):
    """Colore di riempimento come tupla RGB a 2 decimali; None se bianco o assente."""
    color = rect.get('non_stroking_color')
    if color is None:
        return None
    if isinstance(color, (int, float)):
        color = (color,)
    if not all(isinstance(c, (int, float)) for c in color):
        return None
    color = tuple(round(c, 2) for c in color)
    if len(color) == 1:
        color = color * 3
    return None if all(c >= 0.99 for c in color) else color


def _fill_at(page, x, y):
    """Colore della cella nel punto: l'ultimo rettangolo pieno disegnato lì sopra (i bordi sono esclusi)."""
    color = None
    for r in page.rects:
        if r.get('fill') and r['width'] > 3 and r['height'] > 4 \
                and r['x0'] <= x <= r['x1'] and r['top'] <= y <= r['bottom']:
            color = _color(r)
    return color


LEGEND_KEYS = ("MATTIN", "12:00", "12,00", "19:00", "19,00", "RIPASSO")


def _paragraph_next_to(words, r, above):
    """
    Testo del paragrafo subito sopra (o sotto) il rettangolo r: prima riga entro
    40 punti, poi righe a non più di 5 punti l'una dall'altra (oltre è un'altra regola).
    """
    if above:
        near = sorted((w for w in words if w['bottom'] <= r['top'] + 1), key=lambda w: -w['bottom'])
    else:
        near = sorted((w for w in words if w['top'] >= r['bottom'] - 1), key=lambda w: w['top'])
    text, edge, gap = [], r['top'] if above else r['bottom'], 40
    for w in near:
        if w['x1'] <= r['x0'] or w['x0'] >= r['x1']:
            continue
        if (w['bottom'] < edge - gap) if above else (w['top'] > edge + gap):
            break
        text.append(w['text'])
        edge = min(edge, w['top']) if above else max(edge, w['bottom'])
        gap = 5
    return ' '.join(text).upper()


def _legend(page, right):
    """
    Legenda della pulizia bagni, a destra della tabella: barrette colorate vuote
    sopra o sotto un testo di regola ("...ripasso alle ore 19:00", "pulizia del
    mattino", "1° passaggio ore 12:00"). Ritorna la lista dei colori che indicano
    la pulizia; il significato lo dà l'orario del turno (_cleaning_from_time),
    perché la posizione delle barrette rispetto al testo cambia di settimana in
    settimana. I rettangoli colorati con del testo dentro sono evidenziazioni,
    non barrette.
    """
    words = [w for w in page.extract_words() if w['x0'] > right]
    legend = []
    for r in page.rects:
        color = _color(r)
        if not r.get('fill') or color is None or _is_dark(color) or r['x0'] <= right \
                or r['width'] <= 20 or r['height'] <= 4 or color in legend:
            continue
        if any(r['x0'] <= (c['x0'] + c['x1']) / 2 <= r['x1'] and r['top'] <= (c['top'] + c['bottom']) / 2 <= r['bottom']
               for c in page.chars):
            continue
        if any(k in _paragraph_next_to(words, r, above) for above in (True, False) for k in LEGEND_KEYS):
            legend.append(color)
    return legend


def _notes(page, right):
    """
    Indicazioni della settimana: i paragrafi di testo a destra della tabella, uno
    per riquadro (decisione 0008). Righe = parole con lo stesso top (±3 pt);
    paragrafo = righe a meno di 8 pt l'una dall'altra. Si scartano i paragrafi
    senza almeno 2 parole (il numero di pagina). Ritorna
    [{"n", "testo", "pulizia", "asterisco"}]:
    - pulizia: legenda della pulizia bagni del Castello (resa già dall'etichetta
      ambra). Il confronto è senza spazi perché nei PDF vecchi le parole sono
      incollate ("BAGNINUOVICASTELLO…").
    - asterisco: note dei PDF vecchi ("*fino alle ore 15:00") che rimandano a un
      segno nelle celle; nella tabella non c'è, quindi restano solo testo.
    """
    words = sorted((w for w in page.extract_words(use_text_flow=True) if w['x0'] > right),
                   key=lambda w: (round(w['top']), w['x0']))
    lines = []
    for w in words:
        if lines and abs(lines[-1]['top'] - w['top']) < 3:
            lines[-1]['words'].append(w['text'])
            lines[-1]['bottom'] = max(lines[-1]['bottom'], w['bottom'])
        else:
            lines.append({'top': w['top'], 'bottom': w['bottom'], 'words': [w['text']]})
    paragraphs = []
    for line in lines:
        text = " ".join(line['words'])
        if paragraphs and line['top'] - paragraphs[-1]['bottom'] < 8:
            last = paragraphs[-1]
            last['text'] += text if last['text'].endswith("-") else " " + text  # "FF-" + "258-AB"
            last['bottom'] = line['bottom']
        else:
            paragraphs.append({'text': text, 'bottom': line['bottom']})
    notes = []
    for p in paragraphs:
        text = re.sub(r"\s+", " ", p['text']).strip()
        if len(re.findall(r"[^\W\d_]{2,}", text)) < 2:
            continue
        flat = re.sub(r"\s+", "", text).lower()
        notes.append({
            "n": len(notes) + 1,
            "testo": text,
            "pulizia": "castello" in flat and any(k in flat for k in ("bagn", "wc", "puliz")),
            "asterisco": text.startswith("*"),
        })
    return notes


def _is_legend_color(color, legend):
    """Vero se il colore è in legenda, anche in una sfumatura vicina (Excel a volte le cambia)."""
    return any(max(abs(a - b) for a, b in zip(l, color)) <= 0.1 for l in legend)


def _cleaning_from_time(time_range):
    """
    Pulizia bagni dall'orario del turno: "19:00" se il turno comprende le 19:00,
    "Mattina" se comincia prima di mezzogiorno, None altrimenti.
    """
    match = re.fullmatch(r"(\d{2}):(\d{2})-(\d{2}):(\d{2})", time_range or '')
    if not match:
        return None
    start, end = int(match[1]) * 60 + int(match[2]), int(match[3]) * 60 + int(match[4])
    if start <= 19 * 60 <= end:
        return "19:00"
    if start < 12 * 60:
        return "Mattina"
    return None


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
        created = _creation_date(pdf.metadata)
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

        # Le celle unite allargano i bbox di righe e colonne verso destra e verso il
        # basso: affidabili sono solo i bordi sinistro e superiore.
        col_lefts = [col.bbox[0] for col in table.columns] + [table.bbox[2]]
        day_x = {c: (col_lefts[c], col_lefts[c + 1]) for c in days}
        right = max(x1 for _, x1 in day_x.values())
        legend = _legend(page, right)
        notes = _notes(page, right)

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
                # Senza il bordo fra orario e lunedì, pdfplumber unisce le due celle e il
                # nome finisce in colonna 1: le colonne coperte si rileggono per posizione.
                time_box = table.rows[i].cells[1]
                if time_box and time_box[2] > x2 + 1:
                    for c in days:
                        if col_lefts[c] < time_box[2] - 1:
                            cells[c] = _text_in(page, col_lefts[c], row_tops[i], col_lefts[c + 1], row_tops[i + 1])
                    cells[1] = _text_in(page, x1, row_tops[i], x2, row_tops[i + 1])
                is_header = i <= header_idx or cells[1].lower() == 'turno'
                colors = {c: _fill_at(page, sum(day_x[c]) / 2, (row_tops[i] + row_tops[i + 1]) / 2) for c in days}
                rows.append({
                    "riga": i,
                    "etichetta": label,
                    "luogo": None if is_header else location,
                    "orario": '' if is_header else normalize_time(time_cell[i]),
                    "celle": cells,
                    "colori": colors,
                    "header": is_header,
                })

    if len({r["luogo"] for r in rows if r["luogo"]}) < MIN_LOCATIONS:
        raise ValueError("Struttura del PDF non riconosciuta (bordi diversi dal solito?): "
                         "controlla la tabella a mano.")
    return {"days": days, "rows": rows, "legenda": legend, "creato": created, "indicazioni": notes}


def _creation_date(metadata):
    """Data di creazione dai metadati del PDF ('D:AAAAMMGG…'); None se manca o non è valida."""
    match = re.match(r"D:(\d{4})(\d{2})(\d{2})", str((metadata or {}).get('CreationDate') or ''))
    if not match:
        return None
    try:
        return date(int(match[1]), int(match[2]), int(match[3]))
    except ValueError:
        return None


def _first_day_date(days, reference):
    """
    Data del primo giorno dell'intestazione: la più vicina al riferimento, entro 14
    giorni, con quel numero e quel giorno della settimana. None se non c'è o se gli
    altri giorni dell'intestazione non seguono il calendario.
    """
    name, number = days[0]
    matches = [reference + timedelta(offset) for offset in range(-14, 15)]
    matches = [d for d in matches if d.day == int(number) and d.weekday() == DAY_NAMES.index(name)]
    if not matches:
        return None
    start = min(matches, key=lambda d: abs((d - reference).days))
    for i, (name, number) in enumerate(days):
        current = start + timedelta(i)
        if current.day != int(number) or current.weekday() != DAY_NAMES.index(name):
            return None
    return start


def output_filename(table, surname, today=None):
    """
    Nome del PDF generato, ricavato dal contenuto: il nome del file in input cambia
    ogni settimana. L'intestazione dà giorni e numeri, la data di creazione del PDF
    (o la data di oggi) dà mese e anno. Senza una data certa restano i soli numeri.
    """
    surname = re.sub(r'[\\/:*?"<>|]+', ' ', surname).strip()  # niente percorsi o caratteri vietati
    days = [table["days"][col] for col in sorted(table["days"])]
    reference = table.get("creato") or today or date.today()
    start = _first_day_date(days, reference)
    if start is None:
        return f"Turni {surname} dal {int(days[0][1]):02d} al {int(days[-1][1]):02d}.pdf"
    end = start + timedelta(len(days) - 1)
    start_month = "" if start.month == end.month else f" {MONTH_NAMES[start.month - 1]}"
    return f"Turni {surname} dal {start.day:02d}{start_month} al {end.day:02d} {MONTH_NAMES[end.month - 1]}.pdf"


def week_period(table, today=None):
    """
    Periodo da scrivere nel PDF generato, "dal 12 al 18 agosto 2026": stessa fonte di
    output_filename. Mese e anno del primo giorno compaiono solo se cambiano.
    """
    days = [table["days"][col] for col in sorted(table["days"])]
    start = _first_day_date(days, table.get("creato") or today or date.today())
    if start is None:
        return f"dal {int(days[0][1])} al {int(days[-1][1])}"
    end = start + timedelta(len(days) - 1)
    first = f"{start.day}"
    if start.year != end.year:
        first += f" {MONTH_NAMES[start.month - 1]} {start.year}"
    elif start.month != end.month:
        first += f" {MONTH_NAMES[start.month - 1]}"
    return f"dal {first} al {end.day} {MONTH_NAMES[end.month - 1]} {end.year}"


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
    A Giardini del Castello, se il PDF ha la legenda, la pulizia bagni viene dal
    colore della cella: "No" se è bianca; se il colore è in legenda, "19:00" o
    "Mattina" secondo l'orario del turno.
    """
    days = table["days"]
    legend = table.get("legenda", [])
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
                pulizia = ""
                if legend and "giardini del castello" in location.lower():
                    color = row["colori"].get(col_idx)
                    if color is None:
                        pulizia = "No"
                    elif _is_legend_color(color, legend):
                        pulizia = _cleaning_from_time(final_time) or ""
                        if not pulizia:
                            warnings.append(f"{format_day_for_display(day_name)} {day_number}: cella colorata a "
                                            f"{location} su un turno né di mattina né delle 19:00, "
                                            f"controlla la pulizia bagni.")
                    else:
                        warnings.append(f"{format_day_for_display(day_name)} {day_number}: cella colorata a "
                                        f"{location} con un colore che non è in legenda, controlla la pulizia bagni.")
                shifts.append((day_name, day_number, location, final_time, pulizia))

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

# ── Indicazioni della settimana ──────────────────────────────────────────────
# Decisione 0008. Il testo intero va sempre nel PDF. Un'indicazione si collega ai
# turni del primo luogo della tabella che nomina (il soggetto: "l'addetto al
# borgia…"); con la chiave, Gemini la riassume e la restringe a orari e giorni,
# ma solo dentro quel luogo.

GENERIC_WORDS = {'giardini', 'giardino', 'stadio', 'parco', 'villa', 'viale', 'piazza', 'della',
                 'delle', 'dello', 'degli', 'dell', 'dall', 'nell', 'sull', 'alla', 'alle', 'dalla',
                 'nella', 'sulla', 'sede', 'turno', 'via'}
LLM_LABEL_MAX = 45
LLM_TIMEOUT = 40  # secondi per modello: gemini-3.6-flash risponde in 15-50 s


def _plain(text):
    """Minuscole, senza accenti, solo lettere e cifre separate da uno spazio."""
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    return " ".join(re.findall(r"[a-z0-9]+", text))


def _location_words(location):
    return {w for w in _plain(location).split() if len(w) >= 4 and w not in GENERIC_WORDS}


def _table_locations(table):
    """Luoghi di lavoro della tabella, nell'ordine in cui compaiono (stati esclusi)."""
    seen = []
    for row in table["rows"]:
        place = row["luogo"]
        if place and not row["header"] and not is_status_location(place) and place not in seen:
            seen.append(place)
    return seen


def _place_times(table, place):
    """Orari di riga di un luogo, nell'ordine della tabella."""
    times = []
    for row in table["rows"]:
        if row["luogo"] == place and not row["header"] and row["orario"] and row["orario"] not in times:
            times.append(row["orario"])
    return times


def _times_named_in(text, times):
    """
    Orari di un luogo a cui un'indicazione si restringe da sola: quelli che toccano
    un orario scritto nel testo ("turno 10,00-12,00") e quelli della parte del giorno
    nominata ("turno pomeridiano", "antimeridiana", "mattino"). None se il testo non
    restringe niente, o se resterebbero tutti.
    """
    ranges = [normalize_time(m[0]) for m in TIME_RANGE.finditer(text)]
    plain = _plain(text)
    parts = set()
    if re.search(r"\b(antimeridian|mattin)", plain):
        parts.add("Mattina")
    if re.search(r"\bpomerid", plain):
        parts.add("Pomeriggio")
    chosen = [t for t in times
              if any(t == r or _overlap(t, r) for r in ranges if r) or parts & parts_of_day(t)]
    return chosen if chosen and len(chosen) < len(times) else None


def link_notes(table):
    """
    Copia delle indicazioni della tabella con le regole del livello 2: ogni nota
    che non è di pulizia né ad asterisco va sul primo luogo della tabella nominato
    nel testo (parola intera). Ogni nota ha "regole" ([{"luogo", "orari", "giorni"}],
    None = nessuna restrizione), "etichetta" ("Nota N"), "attiva" e "fonte".
    """
    words = {place: _location_words(place) for place in _table_locations(table)}
    notes = []
    for note in table.get("indicazioni", []):
        note = dict(note, etichetta=f"Nota {note['n']}", attiva=True, fonte="parole", regole=[])
        if not note["pulizia"] and not note["asterisco"]:
            tokens = _plain(note["testo"]).split()
            first = None
            for place, place_words in words.items():
                index = next((i for i, t in enumerate(tokens) if t in place_words), None)
                if index is not None and (first is None or index < first[0]):
                    first = (index, place)
            if first:
                times = _place_times(table, first[1])
                note["regole"] = [{"luogo": first[1], "orari": _times_named_in(note["testo"], times),
                                   "giorni": None, "orari_luogo": times}]
        notes.append(note)
    return notes


def notes_for_shift(shift, notes, include_inactive=False):
    """
    Indicazioni attive che valgono per un turno (giorno, numero, luogo, orario, …),
    con l'etichetta della regola che lo prende (Gemini può darne una per turno).
    Un orario scritto nella cella (diverso da quello della riga) vale se coincide o
    si sovrappone a uno degli orari della regola.
    """
    place = _plain(shift[2])
    time = normalize_time(shift[3])
    day = normalize_day_name(shift[0])
    result = []
    for note in notes or []:
        if not note.get("attiva", True) and not include_inactive:
            continue
        for rule in note.get("regole", []):
            if _plain(rule["luogo"]) != place:
                continue
            if rule.get("orari"):
                hours = [normalize_time(t) for t in rule["orari"]]
                row_hours = {normalize_time(t) for t in rule.get("orari_luogo") or []}
                # Un orario di riga del luogo deve coincidere; uno scritto nella cella
                # (che Gemini non vede) basta che si sovrapponga.
                overlaps = time and time not in row_hours and any(_overlap(time, t) for t in hours if t)
                if time not in hours and not overlaps:
                    continue
            if rule.get("giorni") and day not in {normalize_day_name(d) for d in rule["giorni"]}:
                continue
            result.append(dict(note, etichetta=rule.get("etichetta") or note["etichetta"]))
            break
    return result


def _looks_like_name(cell):
    """Cella con una persona ("Damato", "Rizzi Salvatore"), non un segnaposto (CHIUSO, ESTERNO, *****, "addetto presso…")."""
    low = cell.lower().strip()
    return bool(re.search(r"[A-ZÀ-Ý][a-zà-ÿ']", cell)) and "chius" not in low and "estern" not in low \
        and not low.startswith("add")


def llm_request(table, notes):
    """
    Testo della richiesta a Gemini (JSON): le indicazioni da etichettare e le righe
    della tabella come luogo, orario e giorni in cui ci lavora qualcuno. Mai i nomi.
    Ritorna None se non c'è nessuna nota da etichettare.
    """
    todo = [{"n": n["n"], "testo": n["testo"]} for n in notes if n["regole"]]
    if not todo:
        return None
    shifts = {}
    for row in table["rows"]:
        place = row["luogo"]
        if row["header"] or not place or is_status_location(place) or not row["orario"]:
            continue
        days = shifts.setdefault((place, row["orario"]), set())
        for col, (day, _) in table["days"].items():
            if _looks_like_name(row["celle"][col]):
                days.add(DAY_NAMES.index(day) if day in DAY_NAMES else 9)
    rows = [{"luogo": place, "orario": time,
             "giorni": [format_day_for_display(DAY_NAMES[d]) for d in sorted(days) if d < 7]}
            for (place, time), days in shifts.items()]
    return json.dumps({"indicazioni": todo, "turni": rows}, ensure_ascii=False)


LLM_PROMPT = """Sei l'assistente di un servizio di custodia di parchi e strutture.
Ricevi le indicazioni settimanali scritte dal responsabile e l'elenco dei turni
(luogo, orario, giorni in cui c'è qualcuno). Rispondi per TUTTE le indicazioni,
anche quelle che sono solo un'informazione. Per ogni indicazione:
- n: il numero dell'indicazione;
- etichetta: un riassunto in italiano di al massimo 5-6 parole (massimo 45
  caratteri) di cosa deve fare chi è di turno, da mettere accanto al turno.
  Deve contenere il NOME del posto su cui agire, preso dal testo (Manzoni,
  Green Park, via Chieffi…), con l'iniziale maiuscola. Mai parole generiche da
  sole come "giardini", "parco" o "gestisci". Esempi buoni: "Apri e chiudi
  giardini Manzoni", "Chiudi Green Park e giardini Manzoni", "Atleti Simeone
  entrano da via Chieffi";
- turni: a chi è rivolta, cioè l'addetto che deve fare la cosa (il soggetto),
  non i luoghi solo citati. Un elemento per ogni turno (luogo + orario) a cui
  si applica, con i giorni se vale solo in alcuni, e la sua etichetta (stesse
  regole): se l'indicazione chiede cose diverse a turni diversi (es. il turno
  del pomeriggio apre e chiude dei giardini, quello della domenica mattina fa
  l'apertura del mattino), ogni turno ha l'etichetta di quello che tocca a
  lui. Usa esattamente i nomi di luogo e gli orari dell'elenco, un elemento
  per orario. Non mettere turni a cui l'indicazione non si applica. Lascia
  giorni vuoto se vale per tutti i giorni.

Rispondi solo con un oggetto JSON di questa forma:
{"indicazioni": [{"n": 3, "etichetta": "...", "turni": [{"luogo": "...",
"orario": "HH:MM-HH:MM", "giorni": ["domenica"], "etichetta": "..."}]}]}

Dati:
"""

# Fornitori e modelli provati in ordine, saltando quelli senza chiave: se uno
# risponde con un errore (503 per troppo traffico, 429, timeout…) si passa al
# successivo. GROQ_MODEL / GEMINI_MODEL (uno o più nomi separati da virgole)
# sostituiscono la lista di quel fornitore.
LLM_PROVIDERS = (
    ("groq", "GROQ_API_KEY", "GROQ_MODEL", ("qwen/qwen3.8-27b", "openai/gpt-oss-120b", "openai/gpt-oss-20b")),
    ("gemini", "GEMINI_API_KEY", "GEMINI_MODEL", ("gemini-3.6-flash", "gemini-3.8-flash", "gemini-3.5-flash-lite")),
)


def llm_notes(request_json, settings):
    """
    Chiede le etichette al primo modello che risponde bene, nell'ordine di
    LLM_PROVIDERS. settings: dict con le chiavi (GROQ_API_KEY, GEMINI_API_KEY) e
    gli eventuali GROQ_MODEL / GEMINI_MODEL. Ritorna (lista, "fornitore/modello").
    Solleva se non c'è nessuna chiave o se falliscono tutti, con l'errore di ognuno.
    """
    calls = {"groq": _groq_call, "gemini": _gemini_call}
    errors = []
    for provider, key_name, model_name, defaults in LLM_PROVIDERS:
        api_key = (settings or {}).get(key_name)
        if not api_key:
            continue
        override = (settings or {}).get(model_name)
        models = [m.strip() for m in override.split(",")] if override else list(defaults)
        for model in filter(None, models):
            try:
                return calls[provider](request_json, api_key, model), f"{provider} {model}"
            except Exception as e:
                errors.append(f"{provider} {model}: {e}")
    raise RuntimeError("; ".join(errors) or "nessuna chiave impostata")


def _answer_list(text):
    """Lista delle indicazioni da un testo JSON: una lista o {"indicazioni": [...]}."""
    result = json.loads(text)
    if isinstance(result, dict):
        result = result.get("indicazioni")
    if not isinstance(result, list):
        raise ValueError("non è una lista di indicazioni")
    return result


def _http_error(name, response):
    try:
        detail = response.json()["error"]["message"]
    except Exception:
        detail = response.text[:200]
    return RuntimeError(f"{name} ha risposto {response.status_code}: {detail}")


def _groq_call(request_json, api_key, model):
    """Una chiamata a Groq (API compatibile con OpenAI); solleva su qualunque problema."""
    import requests  # solo qui: parser e PDF non ne hanno bisogno
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model, "temperature": 0, "response_format": {"type": "json_object"},
              "messages": [{"role": "system", "content": LLM_PROMPT.rsplit("Dati:", 1)[0]},
                           {"role": "user", "content": "Dati:\n" + request_json}]},
        timeout=LLM_TIMEOUT,
    )
    if response.status_code != 200:
        raise _http_error("Groq", response)
    try:
        return _answer_list(response.json()["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError, ValueError) as e:
        raise RuntimeError(f"Risposta di Groq non leggibile ({e})") from e


def _gemini_call(request_json, api_key, model):
    """Una chiamata REST generateContent a Gemini; solleva su qualunque problema."""
    import requests  # solo qui: parser e PDF non ne hanno bisogno
    day_enum = [format_day_for_display(d) for d in DAY_NAMES]
    schema = {"type": "OBJECT", "required": ["indicazioni"], "properties": {"indicazioni": {
        "type": "ARRAY", "items": {"type": "OBJECT", "required": ["n", "etichetta", "turni"], "properties": {
            "n": {"type": "INTEGER"},
            "etichetta": {"type": "STRING"},
            "turni": {"type": "ARRAY", "items": {"type": "OBJECT", "required": ["luogo", "orario", "etichetta"],
                                                  "properties": {
                "luogo": {"type": "STRING"},
                "orario": {"type": "STRING"},
                "giorni": {"type": "ARRAY", "items": {"type": "STRING", "enum": day_enum}},
                "etichetta": {"type": "STRING"},
            }}},
        }}}}}
    response = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
        json={"contents": [{"role": "user", "parts": [{"text": LLM_PROMPT + request_json}]}],
              "generationConfig": {"temperature": 0, "responseMimeType": "application/json",
                                   "responseSchema": schema}},
        timeout=LLM_TIMEOUT,
    )
    if response.status_code != 200:
        raise _http_error("Gemini", response)
    try:
        data = response.json()
        return _answer_list("".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"]))
    except (KeyError, IndexError, TypeError, ValueError) as e:
        raise RuntimeError(f"Risposta di Gemini non leggibile ({e})") from e


def _overlap(a, b):
    """Vero se due orari HH:MM-HH:MM si sovrappongono in senso stretto (06-12 e 12-18 no)."""
    (a0, a1), (b0, b1) = _time_key(a), _time_key(b)
    return a0 < b1 and b0 < a1


def apply_llm(table, notes, result):
    """
    Applica la risposta di Gemini alle note del livello 2. Abbina per n. Le regole
    di Gemini stanno dentro il luogo e gli orari già trovati: orari (uguale, se no
    quelli che si sovrappongono) e giorni; una lista vuota vale "nessuna
    restrizione". Dopo di loro restano quelle del livello 2, come ripiego per i
    turni che Gemini non ha nominato.
    """
    times = {}
    for row in table["rows"]:
        if row["luogo"] and not row["header"] and row["orario"]:
            times.setdefault(_plain(row["luogo"]), [])
            if row["orario"] not in times[_plain(row["luogo"])]:
                times[_plain(row["luogo"])].append(row["orario"])
    answers = {}
    for item in result:
        if isinstance(item, dict) and isinstance(item.get("n"), int):
            answers.setdefault(item["n"], item)
    updated = []
    for note in notes:
        answer = answers.get(note["n"])
        if not answer or not note["regole"]:
            updated.append(note)
            continue
        note = dict(note, fonte="modello")
        label = str(answer.get("etichetta") or "").strip()
        if 0 < len(label) <= LLM_LABEL_MAX:
            note["etichetta"] = label
        allowed = {_plain(r["luogo"]): r["luogo"] for r in note["regole"]}
        base_hours = {_plain(r["luogo"]): r.get("orari") for r in note["regole"]}
        rules = []
        for turn in answer.get("turni") or []:
            if not isinstance(turn, dict) or _plain(str(turn.get("luogo", ""))) not in allowed:
                continue
            key = _plain(turn["luogo"])
            hours = None
            wanted = normalize_time(str(turn.get("orario") or ""))
            if wanted:
                known = times.get(key, [])
                hours = [wanted] if wanted in known else [t for t in known if _overlap(wanted, t)]
            if base_hours.get(key):  # Gemini restringe gli orari già scelti dal testo, non li allarga
                hours = [h for h in hours or [] if h in base_hours[key]] or base_hours[key]
            days = [normalize_day_name(str(d)) for d in turn.get("giorni") or []]
            days = [d for d in days if d in DAY_NAMES]
            rule_label = str(turn.get("etichetta") or "").strip()
            rules.append({"luogo": allowed[key], "orari": hours or None, "giorni": days or None,
                          "orari_luogo": times.get(key, []),
                          "etichetta": rule_label if 0 < len(rule_label) <= LLM_LABEL_MAX else None})
        if rules:
            # Prima le regole di Gemini (etichetta per turno), poi quelle lette dal
            # testo come ripiego: i turni che Gemini salta tengono la nota, con
            # l'etichetta generale.
            note["regole"] = rules + [dict(r, etichetta=None, ripiego=True) for r in note["regole"]]
        updated.append(note)
    return updated


def notes_with_labels(table, settings=None, call=None):
    """
    Indicazioni con regole ed etichette, e un messaggio sulla fonte. settings ha
    le chiavi e i modelli (vedi llm_notes). Senza chiavi o con un errore restano le
    etichette "Nota N" lette dal testo. call(request_json, settings) sostituisce
    llm_notes (l'app ci mette la cache).
    """
    notes = link_notes(table)
    request_json = llm_request(table, notes)
    if request_json is None:
        return notes, "Nessuna indicazione da collegare ai turni."
    if not any((settings or {}).get(key) for _, key, _, _ in LLM_PROVIDERS):
        return notes, "Etichette \"Nota N\" lette dal testo: nessuna chiave (Groq o Gemini) impostata."
    try:
        result, source = (call or llm_notes)(request_json, settings)
        labeled = apply_llm(table, notes, result)
    except Exception as e:
        return notes, f"Etichette \"Nota N\" lette dal testo: modello non disponibile ({e})."
    if not any(n["fonte"] == "modello" for n in labeled):
        return notes, f"Etichette \"Nota N\" lette dal testo: {source} non ha dato etichette utilizzabili."
    return labeled, f"Etichette e collegamenti da {source}."


def readable_note(text):
    """Un testo scritto tutto in maiuscolo diventa minuscolo con l'iniziale maiuscola."""
    letters = [c for c in text if c.isalpha()]
    if not letters or sum(c.isupper() for c in letters) < 0.8 * len(letters):
        return text
    text = re.sub(r"(^|[.!?]\s+)(\W*)(\w)", lambda m: m[1] + m[2] + m[3].upper(), text.lower())
    text = re.sub(r"\bwc\b", "WC", text)
    text = re.sub(r"\bn\.b\.\)?\s*(\w)", lambda m: m[0][:-1].upper() + m[1].upper(), text, flags=re.IGNORECASE)
    return text


# ── PDF generato ─────────────────────────────────────────────────────────────
# Layout delle decisioni 0007 e 0008: nome e striscia compatta dei sette giorni in
# alto, un blocco per giorno con orari, luoghi ed etichette, poi le indicazioni a
# dimensione fissa. Il corpo prende l'altezza che resta: la scala (fra
# PDF_MIN_SCALE e PDF_MAX_SCALE) si cerca ridisegnando su una pagina di prova.

FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
PDF_FONTS = {"regular": "Inter-Regular", "italic": "Inter-Italic", "semibold": "Inter-SemiBold",
             "bold": "Inter-Bold", "display": "InterDisplay-Bold"}
PDF_MAX_SCALE = 1.45
PDF_MARGIN = 16
PAGE_W, PAGE_H = 210, 297

INK = (17, 24, 39)
MUTED = (107, 114, 128)
FAINT = (156, 163, 175)
LINE = (229, 231, 235)
ACCENT = (30, 64, 175)
STRIP_FILL = (226, 232, 240)   # chiaro: poco inchiostro in stampa
STRIP_TEXT = (30, 41, 59)
AMBER = (146, 64, 14)
AMBER_SOFT = (254, 243, 199)
WHITE = (255, 255, 255)


def _minutes(hhmm):
    hours, minutes = hhmm.split(":")
    return int(hours) * 60 + int(minutes)


def parts_of_day(time_range):
    """
    Parti della giornata occupate da un turno: Notte se comincia prima delle 5,
    Mattina se prima delle 12, Pomeriggio se finisce dopo le 16 o comincia da
    mezzogiorno. 08:45-14:45 è solo Mattina (il pomeriggio è libero), 09-17 tutte e due.
    Orario non leggibile (es. scritto a mano) → nessuna.
    """
    match = re.fullmatch(r"\s*(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})\s*", time_range or "")
    if not match:
        return set()
    start, end = _minutes(match[1]), _minutes(match[2])
    parts = set()
    if start < 5 * 60:
        parts.add("Notte")
    elif start < 12 * 60:
        parts.add("Mattina")
    if end > 16 * 60 or start >= 12 * 60:
        parts.add("Pomeriggio")
    return parts


def _cleaning_label(value):
    value = (value or "").strip()
    if not value or value.lower() == "no":
        return None
    if value == "19:00":
        return "Pulizia bagni alle 19:00"
    if value.lower() == "mattina":
        return "Pulizia bagni di mattina"
    return f"Pulizia bagni: {value}"


def _time_key(time_range):
    """Ordine dentro un giorno: per inizio e poi per fine; orari non leggibili in fondo."""
    match = re.fullmatch(r"\s*(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})\s*", time_range or "")
    return (_minutes(match[1]), _minutes(match[2])) if match else (24 * 60, 24 * 60)


def _days_for_pdf(shifts):
    """
    Per ogni giorno della settimana presente nei turni: (indice 0-6, nome, numero,
    righe, assenza). Le righe sono (luogo, orario, pulizia) in ordine di orario;
    assenza è il nome dello stato se tutte le righe del giorno sono stati, altrimenti None.
    """
    days = {}
    for shift in shifts:
        name = normalize_day_name(shift[0])
        if name not in DAY_NAMES:
            continue
        index = DAY_NAMES.index(name)
        number = str(shift[1]).strip()
        day = days.setdefault(index, {"number": number.lstrip("0") or number, "rows": []})
        day["rows"].append((shift[2], shift[3], shift[4] if len(shift) > 4 else ""))
    result = []
    for index in sorted(days):
        rows = sorted(days[index]["rows"], key=lambda r: _time_key(r[1]))
        statuses = [r for r in rows if is_status_location(r[0])]
        absence = statuses[0][0] if len(statuses) == len(rows) else None
        result.append((index, format_day_for_display(DAY_NAMES[index]).capitalize(),
                       days[index]["number"], rows, absence))
    return result


class _ShiftsPDF(FPDF):
    def __init__(self):
        super().__init__(format="A4")
        self.set_auto_page_break(False)
        self.set_margins(PDF_MARGIN, PDF_MARGIN, PDF_MARGIN)
        for style, name in PDF_FONTS.items():
            self.add_font(style, "", os.path.join(FONT_DIR, name + ".otf"))

    def use(self, font, size, color=INK):
        self.set_font(font, "", size)
        self.set_text_color(*color)

    def write_at(self, x, y, s, font, size, color=INK, align="L", width=0, spacing=0):
        """Testo con la linea di base a y (mm); align C/R dentro width."""
        self.use(font, size, color)
        self.set_char_spacing(spacing)
        if align != "L":
            free = width - self.get_string_width(s)
            x += free if align == "R" else free / 2
        self.text(x, y, s)
        self.set_char_spacing(0)

    def write_fit(self, x, y, s, font, size, color, max_width, min_ratio=0.75, align="L", width=0):
        """Testo che sta in max_width: prima rimpicciolisce fino a min_ratio, poi accorcia con …"""
        current = size
        self.set_font(font, "", current)
        while self.get_string_width(s) > max_width and current > size * min_ratio:
            current -= 0.25
            self.set_font(font, "", current)
        while self.get_string_width(s) > max_width and len(s) > 4:
            s = s[:-2].rstrip() + "…"
        self.write_at(x, y, s, font, current, color, align, width)

    def tabular(self, on):
        """Cifre tabulari di Inter: tutti gli orari hanno la stessa larghezza."""
        if on:
            self.set_text_shaping(use_shaping_engine=True, features={"tnum": True})
        else:
            self.set_text_shaping(False)

    def _fit_label(self, s, size, max_width):
        """Carattere e testo dell'etichetta che stanno in max_width (fino al 75%, poi "…")."""
        current = size
        self.set_font("semibold", "", current)
        while self.get_string_width(s) > max_width and current > size * 0.75:
            current -= 0.25
            self.set_font("semibold", "", current)
        while self.get_string_width(s) > max_width and len(s) > 4:
            s = s[:-2].rstrip() + "…"
        return s, current

    def pill_width(self, s, size, height, number=None):
        self.set_font("semibold", "", size)
        return self.get_string_width(s) + 6 + (height - 0.4 if number else 0)

    def pill(self, x, top, s, size, height, fill=AMBER_SOFT, ink=AMBER, number=None, max_width=None):
        """Etichetta arrotondata; con number, un pallino col numero dell'indicazione davanti."""
        dot = height - 1.6 if number else 0
        pad = dot + 1.2 if number else 0
        if max_width:
            s, size = self._fit_label(s, size, max_width - 6 - pad)
        self.use("semibold", size, ink)
        width = self.get_string_width(s) + 6 + pad
        self.set_fill_color(*fill)
        self.rect(x, top, width, height, style="F", round_corners=True, corner_radius=height / 2)
        if number:
            self.badge(x + 0.8, top + 0.8, number, dot, ink)
            self.use("semibold", size, ink)
        self.text(x + 3 + pad, top + height / 2 + size * 0.127, s)
        return width

    def badge(self, x, top, number, d, ink):
        """Pallino pieno col numero dell'indicazione."""
        self.set_fill_color(*ink)
        self.ellipse(x, top, d, d, style="F")
        size = d * 1.75
        self.use("bold", size, WHITE)
        s = str(number)
        self.text(x + (d - self.get_string_width(s)) / 2, top + d / 2 + size * 0.125, s)


def _pdf_header(pdf, name, period, days):
    """Titolo, nome e periodo a sinistra; a destra la striscia compatta dei sette giorni."""
    left = PDF_MARGIN
    box_w, gap, box_h, top = 11.6, 1.4, 22, 12
    strip_x = PAGE_W - PDF_MARGIN - (7 * box_w + 6 * gap)
    text_w = strip_x - left - 5
    pdf.write_at(left, 18, "TURNI DI LAVORO", "semibold", 8.5, ACCENT, spacing=1.2)
    pdf.write_fit(left, 28.5, name, "display", 22, INK, text_w)
    if period:
        pdf.write_fit(left, 36, period[0].upper() + period[1:], "regular", 11.5, MUTED, text_w)
    short = {"Notte": "Notte", "Mattina": "Matt.", "Pomeriggio": "Pom."}
    by_index = {d[0]: d for d in days}
    for index in range(7):
        x = strip_x + index * (box_w + gap)
        day = by_index.get(index)
        if day is None:  # giorno senza righe (tolte a mano): solo il nome
            pdf.set_draw_color(*LINE)
            pdf.set_line_width(0.3)
            pdf.rect(x, top, box_w, box_h, style="D", round_corners=True, corner_radius=2)
            pdf.write_at(x, top + 4.6, DAY_NAMES[index][:3].upper(), "semibold", 6.5, FAINT, "C", box_w, 0.5)
            continue
        _, day_name, number, rows, absence = day
        if absence:
            pdf.set_draw_color(*LINE)
            pdf.set_line_width(0.35)
            pdf.set_fill_color(*WHITE)
            pdf.rect(x, top, box_w, box_h, style="DF", round_corners=True, corner_radius=2)
            label_color = number_color = MUTED
            labels = [absence.split(" - ")[0]]  # "Riposo - <luogo> (chiuso)": il luogo è nell'elenco
        else:
            pdf.set_fill_color(*STRIP_FILL)
            pdf.rect(x, top, box_w, box_h, style="F", round_corners=True, corner_radius=2)
            label_color, number_color = STRIP_TEXT, INK
            parts = set().union(*(parts_of_day(r[1]) for r in rows if not is_status_location(r[0])))
            labels = [short[p] for p in ("Notte", "Mattina", "Pomeriggio") if p in parts]
        pdf.write_at(x, top + 4.6, day_name[:3].upper(), "semibold", 6.5, label_color, "C", box_w, 0.5)
        pdf.write_at(x, top + 11, number, "display", 12, number_color, "C", box_w)
        label_y = top + {0: 0, 1: 17.2, 2: 15.6, 3: 14.4}[len(labels)]
        for label in labels:
            pdf.write_fit(x, label_y, label, "semibold", 6, label_color, box_w - 1.5, 0.6, "C", box_w)
            label_y += 3
    return top + box_h + 7


def _row_pills(index, number, place, time, cleaning, notes):
    """Etichette di una riga: pulizia bagni (ambra) e indicazioni (col loro colore e numero)."""
    pills = []
    label = _cleaning_label(cleaning)
    if label:
        pills.append((label, AMBER_SOFT, AMBER, None))
    for note in notes_for_shift((DAY_NAMES[index], number, place, time), notes):
        pills.append((note["etichetta"], *note["colori"], note["n"]))
    return pills


def _pdf_body(pdf, days, notes, y, k):
    """Elenco dei giorni a scala k; ritorna la y finale. Le etichette vanno accanto al
    luogo se ci stanno tutte sulla stessa riga, altrimenti sotto, una per riga."""
    left, width = PDF_MARGIN, PAGE_W - 2 * PDF_MARGIN
    size = 12 * k
    pdf.set_font("semibold", "", size)
    pdf.tabular(True)
    time_w = pdf.get_string_width("00:00 – 00:00")
    pdf.tabular(False)
    x_time = left + 40 * k
    x_place = x_time + time_w + 6 * k
    place_w = left + width - x_place
    pill_size, pill_h, pill_gap = 9 * k, 6 * k, 2.5 * k
    for index, name, number, rows, absence in days:
        pdf.write_at(left, y + 6 * k, f"{name} {number}", "bold", size, FAINT if absence else INK)
        if absence:
            pdf.write_fit(x_time, y + 6 * k, absence, "italic", size, MUTED, left + width - x_time)
            y += 9.5 * k
        else:
            for place, time, cleaning in rows:
                if is_status_location(place):  # es. permesso in un giorno di lavoro
                    pdf.write_fit(x_place, y + 6 * k, place, "italic", size, MUTED, place_w)
                    y += 8.5 * k
                    continue
                pdf.tabular(True)
                pdf.write_at(x_time, y + 6 * k, time.replace("-", " – ") if time else "—", "semibold", size, INK)
                pdf.tabular(False)
                pills = _row_pills(index, number, place, time, cleaning, notes)
                pdf.set_font("regular", "", size)
                place_text_w = pdf.get_string_width(place)
                inline_w = sum(pdf.pill_width(p[0], pill_size, pill_h, p[3]) + pill_gap for p in pills)
                if pills and place_text_w + 3 * k + inline_w <= place_w:
                    pdf.write_at(x_place, y + 6 * k, place, "regular", size, INK)
                    x = x_place + place_text_w + 3 * k
                    for label, fill, ink, n in pills:
                        x += pdf.pill(x, y + 1.6 * k, label, pill_size, pill_h, fill, ink, n) + pill_gap
                    y += 8.5 * k
                else:
                    pdf.write_fit(x_place, y + 6 * k, place, "regular", size, INK, place_w)
                    y += 8.5 * k
                    for label, fill, ink, n in pills:
                        pdf.pill(x_place, y - 0.5 * k, label, pill_size, pill_h, fill, ink, n, place_w)
                        y += 7 * k
            y += 1.5 * k
        pdf.set_draw_color(*LINE)
        pdf.set_line_width(0.3)
        pdf.line(left, y, left + width, y)
        y += 2.5 * k
    return y


NOTE_COLORS = [((219, 234, 254), (30, 64, 175)), ((220, 252, 231), (22, 101, 52)),
               ((237, 233, 254), (91, 33, 182)), ((252, 231, 243), (157, 23, 77)),
               ((204, 251, 241), (17, 94, 89)), ((241, 245, 249), (51, 65, 85))]
NOTE_SIZE_MINE = 9
NOTE_SIZES_OTHER = (7.5, 7, 6.5)
PDF_MIN_SCALE = 0.6


def _pdf_notes(pdf, mine, others, y, other_size):
    """Indicazioni a dimensione fissa: prima quelle dei tuoi turni, poi le altre in grigio."""
    left, width = PDF_MARGIN, PAGE_W - 2 * PDF_MARGIN
    for title, items, size, color, title_color in (
            ("INDICAZIONI PER I TUOI TURNI", mine, NOTE_SIZE_MINE, INK, ACCENT),
            ("ALTRE INDICAZIONI DELLA SETTIMANA", others, other_size, MUTED, MUTED)):
        if not items:
            continue
        pdf.write_at(left, y + 4, title, "semibold", 7.5, title_color, spacing=1.0)
        y += 7
        dot = size * 0.5
        for note in items:
            pdf.badge(left, y + 0.3, note["n"], dot, note["colori"][1])
            pdf.use("regular", size, color)
            pdf.set_xy(left + dot + 2.5, y)
            pdf.multi_cell(width - dot - 2.5, size * 0.43, readable_note(note["testo"]), align="L")
            y = pdf.get_y() + 2.2
        y += 1
    return y


def _split_notes(days, notes):
    """Colori alle indicazioni, e divisione fra quelle dei turni della persona e le altre."""
    colored, i = [], 0
    for note in notes or []:
        if note.get("pulizia"):
            colors = (AMBER_SOFT, AMBER)
        else:
            colors = NOTE_COLORS[i % len(NOTE_COLORS)]
            i += 1
        colored.append(dict(note, colori=colors))
    linked = set()
    has_cleaning = False
    for index, _, number, rows, _ in days:
        for place, time, cleaning in rows:
            shift = (DAY_NAMES[index], number, place, time)
            linked |= {n["n"] for n in notes_for_shift(shift, colored, include_inactive=True)}
            has_cleaning = has_cleaning or bool(_cleaning_label(cleaning))
    mine = [n for n in colored if n["n"] in linked or (has_cleaning and n.get("pulizia"))]
    others = [n for n in colored if n not in mine]
    return colored, mine, others


def write_shifts_to_pdf(shifts, out_path, surname, period=None, notes=None):
    """
    PDF di una pagina con i turni della settimana e le indicazioni (decisioni 0007 e
    0008); period è il testo di week_period, notes quello di notes_with_labels.
    Ritorna (percorso, avviso): l'avviso è None, oppure dice che il contenuto non
    sta nella pagina nemmeno alla scala minima.
    """
    days = _days_for_pdf(shifts)
    notes, mine, others = _split_notes(days, notes)
    name = " ".join(w[:1].upper() + w[1:] for w in surname.split())
    pdf = _ShiftsPDF()
    pdf.add_page()
    top = _pdf_header(pdf, name, period, days)
    probe = _ShiftsPDF()
    probe.add_page()
    bottom = PAGE_H - PDF_MARGIN
    warning = None
    for other_size in NOTE_SIZES_OTHER:
        notes_h = _pdf_notes(probe, mine, others, 0, other_size) + 3 if notes else 0
        if _pdf_body(probe, days, notes, top, PDF_MIN_SCALE) <= bottom - notes_h:
            break
    else:
        warning = "Turni e indicazioni non stanno in una pagina: controlla il fondo del PDF."
    if _pdf_body(probe, days, notes, top, PDF_MAX_SCALE) <= bottom - notes_h:
        scale = PDF_MAX_SCALE
    else:  # dove vanno le etichette dipende dalla scala: si cerca per bisezione
        low, high = PDF_MIN_SCALE, PDF_MAX_SCALE
        for _ in range(12):
            mid = (low + high) / 2
            low, high = (mid, high) if _pdf_body(probe, days, notes, top, mid) <= bottom - notes_h else (low, mid)
        scale = low
    y = _pdf_body(pdf, days, notes, top, scale)
    if notes:
        _pdf_notes(pdf, mine, others, y + 3, other_size)
    pdf.output(out_path)
    print(f"File '{out_path}' creato con successo!")
    return out_path, warning

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
        if file.lower().endswith('.pdf') and not os.path.basename(file).lower().startswith('turni '):
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

    settings = {k: os.environ.get(k) for _, key, model, _ in LLM_PROVIDERS for k in (key, model)}
    notes, source = notes_with_labels(table, settings)
    print(source)
    _, warning = write_shifts_to_pdf(shifts_sorted, output_filename(table, surname), surname, week_period(table), notes)
    if warning:
        print(f"ATTENZIONE: {warning}")
    input("Premi Invio per uscire...")

if __name__ == "__main__":
    main()
