import pdfplumber
import os
import re
import glob
from datetime import datetime
from fpdf import FPDF
import sys
print("write_shifts_to_pdf loaded", file=sys.stderr)

# Variabile globale per controllare la modalità debug
DEBUG_MODE = False

def debug_print(*args, **kwargs):
    """Stampa solo se la modalità debug è attiva."""
    if DEBUG_MODE:
        print(*args, **kwargs)

def normalize_day_name(day_name):
    """Normalizza il nome del giorno, convertendo mercoledì in mercoledi'."""
    day_name = day_name.lower().strip()
    if day_name == 'mercoledì':
        return "mercoledi'"
    return day_name

def format_day_for_display(day_name):
    """Formatta il nome del giorno per la visualizzazione (mercoledi' -> mercoledì)."""
    if day_name == "mercoledi'":
        return "mercoledì"
    return day_name

def get_hardcoded_structure():
    """
    Definisce la struttura hardcoded del PDF basata sulla posizione delle righe.
    Ogni voce contiene: (row_index, location, time_slot, notes)
    """
    structure = {
        # Giardini del Castello
        0: ("Giardini del Castello", "08:00-14:00", ""),
        1: ("Giardini del Castello", "08:00-14:00", ""),
        2: ("Giardini del Castello", "14:00-21:00", ""),
        3: ("Giardini del Castello", "16:00-22:00", ""),
        4: ("Giardini del Castello", "16:00-22:00", ""),
        
        # Villa Bonelli
        5: ("Villa Bonelli", "09:00-13:00", ""),
        6: ("Villa Bonelli", "16:00-20:00", ""),
        
        # Giardini v.le Giannone
        7: ("Giardini v.le Giannone", "08:30-12:30", ""),
        8: ("Giardini v.le Giannone", "16:30-20:30", ""),
        
        # Parco dell'Umanità
        9: ("Parco dell'Umanità", "09:00-11:00", ""),
        10: ("Parco dell'Umanità", "16:00-18:00", ""),
        11: ("Parco dell'Umanità", "16:00-20:00", ""),
        
        # Giardini viale Manzoni-Via Da Vinci
        12: ("Giardini viale Manzoni-Via Da Vinci", "10:00-12:00", ""),
        13: ("Giardini viale Manzoni-Via Da Vinci", "16:15-20:15", ""),
        14: ("Giardini viale Manzoni-Via Da Vinci", "10:30-12:30", ""),
        15: ("Giardini viale Manzoni-Via Da Vinci", "17:15-20:15", ""),
        
        # Paladisfida Borgia
        16: ("Paladisfida Borgia", "14:30-23:30", ""),
        17: ("Paladisfida Borgia", "08:15-13:15", ""),
        18: ("Paladisfida Borgia", "14:30-23:30", ""),
        
        # Canne della Battaglia
        19: ("Canne della Battaglia", "08:45-14:45", ""),
        
        # Cantina della sfida
        20: ("Cantina della sfida", "09:00-13:00", ""),
        21: ("Cantina della sfida", "15:00-19:00", ""),
        
        # Stadio Puttilli
        22: ("Stadio Puttilli", "08:00-12:00", ""),
        23: ("Stadio Puttilli", "10:00-13:00", ""),
        24: ("Stadio Puttilli", "15:00-18:00", ""),
        
        # Giardini via Chieffi
        25: ("Giardini via Chieffi", "10:00-13:00", ""),
        26: ("Giardini via Chieffi", "17:00-20:00", ""),
        
        # Giardini Stadio Simeone
        27: ("Giardini Stadio Simeone", "10:00-13:00", ""),
        28: ("Giardini Stadio Simeone", "17:00-20:00", ""),
        
        # Palazzo di Città
        29: ("Palazzo di Città", "06:00-12:00", ""),
        30: ("Palazzo di Città", "12:00-18:00", ""),
        31: ("Palazzo di Città", "18:00-24:00", ""),
        32: ("Palazzo di Città", "06:00-14:00", ""),
        33: ("Palazzo di Città", "14:00-22:00", ""),
        
        # Cimitero
        34: ("Cimitero", "07:30-12:30", ""),
        35: ("Cimitero", "15:00-19:00", ""),
        36: ("Cimitero", "06:30-13:30", ""),
        
        # Sede Bar.S.A.
        39: ("Sede Bar.S.A.", "00:00-06:20", ""),
        40: ("Sede Bar.S.A.", "06:00-12:20", ""),
        41: ("Sede Bar.S.A.", "12:00-18:20", ""),
        42: ("Sede Bar.S.A.", "13:00-19:20", ""),
        43: ("Sede Bar.S.A.", "18:00-24:00", ""),
        44: ("Sede Bar.S.A.", "00:00-08:00", ""),
        45: ("Sede Bar.S.A.", "08:00-16:00", ""),
        46: ("Sede Bar.S.A.", "16:00-24:00", ""),
        
        48: ("Distribuzione Prodotti", "15:00-20:00", ""),
        
        # Riposo
        50: ("Riposo", "", ""),
        51: ("Riposo", "", ""),
        52: ("Riposo", "", ""),
        53: ("Riposo", "", ""),
        54: ("Riposo", "", ""),
        55: ("Riposo", "", ""),
        56: ("Riposo", "", ""),
        
        # 2° Riposo
        58: ("2° Riposo", "", ""),
        59: ("2° Riposo", "", ""),
        60: ("2° Riposo", "", ""),
        61: ("2° Riposo", "", ""),
        62: ("2° Riposo", "", ""),
        
        # Ferie
        64: ("Ferie", "", ""),
        65: ("Ferie", "", ""),
        66: ("Ferie", "", ""),
        67: ("Ferie", "", ""),
        
        # Malattia
        69: ("Malattia", "", ""),
        70: ("Malattia", "", ""),
        
        # Permessi Vari
        72: ("Permessi Vari", "", ""),
        73: ("Permessi Vari", "", ""),
    }
    
    return structure

def read_pdf_tables(file_path):
    """Read tables from PDF file using pdfplumber."""
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
    """
    Wrapper compatibile con l'interfaccia Streamlit.
    Restituisce le tabelle estratte dal PDF (lista di tables).
    """
    return read_pdf_tables(file_path)


def extract_days_from_header(tables):
    """Extract days and their numbers from the table header."""
    days = []
    for table in tables:
        if not table:
            continue
        
        # Cerca nei primi righe della tabella
        for row_idx in range(min(3, len(table))):
            row = table[row_idx]
            if not row:
                continue
                
            debug_print(f"Debug: Analizzando header riga {row_idx}: {row}")
            
            for cell in row:
                if cell:
                    cell_text = str(cell).strip()
                    # Cerca giorni - pattern migliorato per catturare caratteri accentati e apostrofi
                    match = re.match(r"([a-zàèéìòù']+)\s+(\d+)", cell_text, re.IGNORECASE)
                    if match:
                        giorno = normalize_day_name(match.group(1))
                        if giorno in ['lunedì', 'martedì', "mercoledi'", 'giovedì', 'venerdì', 'sabato', 'domenica']:
                            days.append((giorno, match.group(2)))
                            debug_print(f"Debug: Trovato giorno: {giorno} {match.group(2)}")
            
            if days:  # Se abbiamo trovato i giorni in questa riga, esci
                break
        
        if days:  # Se abbiamo trovato i giorni in questa tabella, esci
            break
    
    debug_print(f"Debug: Giorni estratti: {days}")
    return days

def extract_shifts_for_person_hardcoded(tables, surname):
    """Extract shifts for the specified surname using hardcoded structure."""
    if not tables:
        return []
    
    days = extract_days_from_header(tables)
    if not days:
        print("Errore: Non è stato possibile trovare i giorni nelle tabelle")
        return []
    
    shifts = []
    days_with_shifts = set()
    structure = get_hardcoded_structure()
    
    debug_print(f"\nCercando turni per: {surname}")
    
    for table in tables:
        if not table:
            continue
        
        debug_print(f"\nDebug: Processando tabella con {len(table)} righe")
        
        # Trova l'header con i giorni
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
        
        # Analizza ogni riga dopo l'header usando la struttura hardcoded
        for row_idx in range(header_row_idx + 1, len(table)):
            row = table[row_idx]
            if not row or all(cell is None or str(cell).strip() == '' for cell in row):
                continue
            
            # Calcola l'indice relativo alla struttura hardcoded
            structure_idx = row_idx - header_row_idx - 1
            
            debug_print(f"\nDebug: Riga {row_idx} (struttura idx {structure_idx}): {[str(cell)[:30] if cell else None for cell in row[:5]]}")
            
            # Ottieni informazioni dalla struttura hardcoded
            if structure_idx in structure and structure[structure_idx] is not None:
                location, time_slot, notes = structure[structure_idx]
                debug_print(f"Debug: Struttura hardcoded - Location: '{location}', Time: '{time_slot}', Notes: '{notes}'")
            else:
                debug_print(f"Debug: Struttura hardcoded non definita per riga {structure_idx}, uso fallback")
                location = "Turno non definito"
                time_slot = ""
                notes = ""
            
            # Cerca il surname nelle colonne dei giorni
            for col_idx, cell in enumerate(row):
                if cell and surname.lower() in str(cell).lower():
                    if col_idx in day_columns:
                        day_name, day_number = day_columns[col_idx]
                        
                        debug_print(f"Debug: Trovato '{surname}' in {day_name} {day_number} (colonna {col_idx})")
                        
                        days_with_shifts.add(day_name)
                        
                        # Usa le informazioni hardcoded
                        final_location = location if location else "Turno"
                        final_time = time_slot if time_slot else ""
                        
                        # Controlla se è un giorno di riposo/chiuso
                        if "CHIUSO" in final_location.upper() or "CHIUSA" in final_location.upper():
                            shifts.append((day_name, day_number, "Riposo - " + final_location, "", ""))
                        elif "riposo" in final_location.lower() or "ferie" in final_location.lower():
                            shifts.append((day_name, day_number, final_location, "", ""))
                        else:
                            # Aggiungi campo pulizia bagni (vuoto per ora, sarà gestito più avanti)
                            shifts.append((day_name, day_number, final_location, final_time, ""))
                        
                        debug_print(f"Debug: Aggiunto turno: {day_name} {day_number}, {final_location}, {final_time}")
    
    # Aggiungi giorni mancanti come "Riposo"
    for day_name, day_number in days:
        if day_name not in days_with_shifts:
            shifts.append((day_name, day_number, "Riposo", "", ""))
    
    debug_print(f"\nDebug: Totale turni trovati: {len(shifts)}")
    for shift in shifts:
        debug_print(f"Debug: {shift}")
    
    return shifts

def has_giardini_castello(shifts):
    """Controlla se tra i turni c'è almeno uno ai 'Giardini del Castello'."""
    for shift in shifts:
        location = shift[2]  # Il luogo è il terzo elemento della tupla
        if "giardini del castello" in location.lower():
            return True
    return False

def print_shifts(shifts):
    """Stampa i turni."""
    has_bagni = has_giardini_castello(shifts)
    
    print("\nTurni attuali:")
    print("-" * (100 if has_bagni else 80))
    
    if has_bagni:
        print(f"{'N.':<3} {'Giorno':<12} {'Data':<6} {'Luogo':<35} {'Orario':<15} {'Pulizia bagni':<12}")
    else:
        print(f"{'N.':<3} {'Giorno':<12} {'Data':<6} {'Luogo':<35} {'Orario':<15}")
    
    print("-" * (100 if has_bagni else 80))
    
    for i, shift in enumerate(shifts, 1):
        day, day_number, location, time = shift[:4]
        pulizia_bagni = shift[4] if len(shift) > 4 else ""
        
        # Formatta il giorno per la visualizzazione
        day_display = format_day_for_display(day)
        
        if has_bagni:
            print(f"{i:<3} {day_display:<12} {day_number:<6} {location:<35} {time:<15} {pulizia_bagni:<12}")
        else:
            print(f"{i:<3} {day_display:<12} {day_number:<6} {location:<35} {time:<15}")
    
    print("-" * (100 if has_bagni else 80))

def add_new_shift(shifts):
    """Aggiunge un nuovo turno alla lista."""
    print("\n--- Aggiunta nuovo turno ---")
    
    # Giorni validi
    giorni_validi = ['lunedì', 'martedì', "mercoledi'", 'mercoledì', 'giovedì', 'venerdì', 'sabato', 'domenica']
    
    # Chiedi il giorno
    while True:
        giorno = input("Inserisci il giorno (lunedì, martedì, mercoledì, ecc.): ").strip()
        giorno_normalizzato = normalize_day_name(giorno)
        if giorno_normalizzato in ['lunedì', 'martedì', "mercoledi'", 'giovedì', 'venerdì', 'sabato', 'domenica']:
            giorno = giorno_normalizzato
            break
        print("Giorno non valido. Usa uno dei seguenti: lunedì, martedì, mercoledì, giovedì, venerdì, sabato, domenica")
    
    # Chiedi la data
    while True:
        try:
            data = input("Inserisci la data (numero del giorno): ").strip()
            if data.isdigit() and 1 <= int(data) <= 31:
                break
            print("Data non valida. Inserisci un numero tra 1 e 31.")
        except ValueError:
            print("Data non valida. Inserisci un numero.")
    
    # Chiedi il luogo
    luogo = input("Inserisci il luogo: ").strip()
    if not luogo:
        luogo = "Turno"
    
    # Chiedi l'orario
    orario = input("Inserisci l'orario (es: 08:00-14:00, opzionale): ").strip()
    
    # Gestisci pulizia bagni se necessario
    pulizia_bagni = ""
    if "giardini del castello" in luogo.lower():
        pulizia_bagni = input("Pulizia bagni (Sì/No): ").strip()
        if not pulizia_bagni:
            pulizia_bagni = "No"
    
    # Chiedi la posizione dove inserire il nuovo turno
    while True:
        try:
            print(f"\nDove vuoi inserire il nuovo turno?")
            print(f"• Inserisci un numero da 1 a {len(shifts)} per inserire in quella posizione")
            print(f"• Inserisci {len(shifts) + 1} (o premi Invio) per aggiungere in fondo")
            
            posizione_input = input("Posizione: ").strip()
            
            if not posizione_input:
                # Se l'utente preme solo Invio, aggiungi in fondo
                posizione = len(shifts)
                break
            
            posizione = int(posizione_input) - 1  # Converti a indice 0-based
            
            if 0 <= posizione <= len(shifts):
                break
            else:
                print(f"Posizione non valida. Inserisci un numero tra 1 e {len(shifts) + 1}.")
        except ValueError:
            print("Input non valido. Inserisci un numero.")
    
    # Crea il nuovo turno
    nuovo_turno = (giorno, data, luogo, orario, pulizia_bagni)
    
    # Inserisci il turno nella posizione specificata
    shifts.insert(posizione, nuovo_turno)
    
    # Formatta il giorno per la visualizzazione
    giorno_display = format_day_for_display(giorno)
    
    print(f"✓ Nuovo turno aggiunto alla posizione {posizione + 1}: {giorno_display} {data} - {luogo} - {orario}")
    if pulizia_bagni:
        print(f"  Pulizia bagni: {pulizia_bagni}")
    
    return shifts

def modify_shifts(shifts):
    """Permette di modificare i turni e aggiungere nuovi turni prima di stampare il PDF."""
    has_bagni = has_giardini_castello(shifts)
    
    while True:
        try:
            print("\n--- OPZIONI ---")
            print("• Inserisci il numero della riga da modificare (es: 1,2,3 per più righe)")
            print("• Scrivi 'aggiungi' per aggiungere un nuovo turno")
            print("• Scrivi '0' per finire")
            
            choice = input("\nCosa vuoi fare? ").strip()
            
            if choice == '0':
                break
            elif choice.lower() in ['aggiungi', 'add', 'nuovo']:
                shifts = add_new_shift(shifts)
                # Aggiorna has_bagni dopo l'aggiunta
                has_bagni = has_giardini_castello(shifts)
                print_shifts(shifts)
                continue
            
            # Gestisce sia singole righe che righe multiple separate da virgola
            row_numbers = []
            if ',' in choice:
                # Righe multiple
                try:
                    row_numbers = [int(x.strip()) - 1 for x in choice.split(',')]
                except ValueError:
                    print("Formato non valido. Usa numeri separati da virgole (es: 1,2,3)")
                    continue
            else:
                # Singola riga
                try:
                    row_numbers = [int(choice) - 1]
                except ValueError:
                    print("Input non valido. Inserisci un numero, 'aggiungi' o '0'.")
                    continue
            
            # Verifica che tutti i numeri di riga siano validi
            valid_rows = []
            for row_num in row_numbers:
                if 0 <= row_num < len(shifts):
                    valid_rows.append(row_num)
                else:
                    print(f"Numero riga {row_num + 1} non valido (deve essere tra 1 e {len(shifts)})")
            
            if not valid_rows:
                print("Nessuna riga valida selezionata.")
                continue
            
            # Se c'è più di una riga, chiedi se applicare le stesse modifiche a tutte
            if len(valid_rows) > 1:
                print(f"\nHai selezionato {len(valid_rows)} righe:")
                for row_num in valid_rows:
                    shift = shifts[row_num]
                    day, day_number, location, time = shift[:4]
                    day_display = format_day_for_display(day)
                    print(f"  {row_num + 1}. {day_display} {day_number} - {location} - {time}")
                
                batch_mode = input("\nVuoi applicare le stesse modifiche a tutte le righe? (s/n): ").strip().lower()
                batch_mode = batch_mode in ['s', 'si', 'sì', 'y', 'yes']
            else:
                batch_mode = False
            
            if batch_mode:
                # Modalità batch: stesse modifiche per tutte le righe
                print("\nInserisci le modifiche da applicare a tutte le righe selezionate:")
                
                # Prendi il primo turno come riferimento
                first_shift = shifts[valid_rows[0]]
                old_location = first_shift[2]
                old_time = first_shift[3]
                
                print(f"Luogo di riferimento: '{old_location}'")
                print(f"Orario di riferimento: '{old_time}'")
                
                # Modifica luogo
                new_location = input(f"Nuovo luogo (premi Invio per mantenere invariato): ").strip()
                
                # Modifica orario
                new_time = input(f"Nuovo orario (premi Invio per mantenere invariato): ").strip()
                
                # Gestisci pulizia bagni se necessario
                new_pulizia_bagni = ""
                if has_bagni:
                    new_pulizia_bagni = input(f"Pulizia bagni per turni ai Giardini del Castello (Sì/No, vuoto per mantenere invariato): ").strip()
                
                # Applica le modifiche a tutte le righe selezionate
                for row_num in valid_rows:
                    shift = list(shifts[row_num])
                    day, day_number, old_loc, old_tm = shift[:4]
                    
                    # Applica le modifiche solo se specificate
                    final_location = new_location if new_location else old_loc
                    final_time = new_time if new_time else old_tm
                    
                    # Gestisci pulizia bagni
                    pulizia_bagni = ""
                    if has_bagni:
                        if "giardini del castello" in final_location.lower():
                            if new_pulizia_bagni:
                                pulizia_bagni = new_pulizia_bagni
                            else:
                                pulizia_bagni = shift[4] if len(shift) > 4 else "No"
                        else:
                            pulizia_bagni = shift[4] if len(shift) > 4 else ""
                    
                    # Aggiorna il turno
                    shifts[row_num] = (day, day_number, final_location, final_time, pulizia_bagni)
                    
                    day_display = format_day_for_display(day)
                    print(f"✓ Riga {row_num + 1} aggiornata: {day_display} {day_number} - {final_location} - {final_time}")
                    if has_bagni and pulizia_bagni:
                        print(f"  Pulizia bagni: {pulizia_bagni}")
            
            else:
                # Modalità individuale: modifica ogni riga separatamente
                for row_num in valid_rows:
                    shift = list(shifts[row_num])
                    day, day_number, old_location, old_time = shift[:4]
                    
                    day_display = format_day_for_display(day)
                    print(f"\n--- Modifica turno per {day_display} {day_number} (riga {row_num + 1}) ---")
                    print(f"Luogo attuale: '{old_location}'")
                    print(f"Orario attuale: '{old_time}'")
                    
                    # Modifica luogo
                    new_location = input(f"Nuovo luogo (premi Invio per mantenere '{old_location}'): ").strip()
                    if not new_location:
                        new_location = old_location
                    
                    # Modifica orario
                    new_time = input(f"Nuovo orario (premi Invio per mantenere '{old_time}'): ").strip()
                    if not new_time:
                        new_time = old_time
                    
                    # Gestisci pulizia bagni se necessario
                    pulizia_bagni = ""
                    if has_bagni and "giardini del castello" in new_location.lower():
                        old_pulizia = shift[4] if len(shift) > 4 else "No"
                        pulizia_bagni = input(f"Pulizia bagni (Sì/No, premi Invio per '{old_pulizia}'): ").strip()
                        if not pulizia_bagni:
                            pulizia_bagni = old_pulizia
                    elif has_bagni:
                        pulizia_bagni = shift[4] if len(shift) > 4 else ""
                    
                    # Aggiorna il turno
                    shifts[row_num] = (day, day_number, new_location, new_time, pulizia_bagni)
                    
                    print(f"✓ Turno aggiornato: {day_display} {day_number} - {new_location} - {new_time}")
                    if has_bagni and pulizia_bagni:
                        print(f"  Pulizia bagni: {pulizia_bagni}")
            
            # Mostra i turni aggiornati
            print_shifts(shifts)
                
        except Exception as e:
            print(f"Errore durante la modifica: {e}")
            print("Riprova con un formato valido.")
    
    return shifts
    
def sort_days(shifts):
    """Sort shifts by day of the week and then by time."""
    day_order = {
        'lunedì': 1,
        'martedì': 2,
        "mercoledi'": 3,
        'giovedì': 4,
        'venerdì': 5,
        'sabato': 6,
        'domenica': 7
    }

    def get_day_number(shift):
        day = normalize_day_name(shift[0])
        return day_order.get(day, 8)

    def get_time(shift):
        """Extract the time from a shift (if any)."""
        time_str = shift[3]
        if time_str:
            try:
                start_time = time_str.split('-')[0].strip()
                return datetime.strptime(start_time, "%H:%M")
            except (ValueError, IndexError):
                return datetime.max
        return datetime.max

    def sort_key(shift):
        return (get_day_number(shift), get_time(shift))
    
    return sorted(shifts, key=sort_key)

def write_shifts_to_pdf(shifts_or_tables, input_filename, surname):
    """Write shifts to PDF file.
    shifts_or_tables può essere:
      - la lista di turni ([(giorno, data, luogo, orario, pulizia), ...]) oppure
      - le tabelle estratte da pdfplumber (quello che restituisce parse_pdf)
    Se riceve le tabelle, estrae i turni per il cognome fornito.
    """
    # Se l'argomento passato è probabilmente le tabelle estratte da pdfplumber,
    # convertile in 'shifts' usando la funzione di estrazione esistente.
    shifts = shifts_or_tables
    if isinstance(shifts_or_tables, list) and shifts_or_tables:
        # tipica struttura: lista di tabelle, ogni tabella è lista di righe (liste)
        # riconosciamo le tabelle verificando che il primo elemento sia una lista
        # e che i suoi elementi interni siano liste (righe).
        first = shifts_or_tables[0]
        if isinstance(first, list) and (len(first) == 0 or isinstance(first[0], list)):
            tables = shifts_or_tables
            shifts = extract_shifts_for_person_hardcoded(tables, surname)
    
    shifts = sort_days(shifts)
    
    # ora 'shifts' è garantito essere la lista di tuple dei turni (o [])
    # segue il codice esistente

    # Estrai la parte finale del nome del file di input per creare il nome del file di output
    match = re.search(r"DAL.*\.pdf", input_filename, re.IGNORECASE)
    if match:
        output_filename = f"Turni {surname} " + match.group(0).lower()
    else:
        output_filename = f"Turni {surname}.pdf"

    # Controlla se c'è bisogno della colonna pulizia bagni
    has_bagni = has_giardini_castello(shifts)
    
    # Inizializza i valori di default per la pulizia bagni
    if has_bagni:
        updated_shifts = []
        for shift in shifts:
            if len(shift) < 5:
                # Aggiungi il campo pulizia bagni se mancante
                if "giardini del castello" in shift[2].lower():
                    updated_shifts.append(shift + ("No",))
                else:
                    updated_shifts.append(shift + ("",))
            else:
                # Se il campo esiste già, assicurati che sia valorizzato correttamente
                pulizia_value = shift[4]
                if "giardini del castello" in shift[2].lower() and not pulizia_value:
                    updated_shifts.append(shift[:4] + ("No",))
                else:
                    updated_shifts.append(shift)
        shifts = updated_shifts

    # Crea il documento PDF
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Aggiungi il titolo
    pdf.set_font("Arial", "B", size=17)
    pdf.cell(200, 10, txt=f"Turni di lavoro {surname}", ln=True, align='C')
    pdf.ln(10)

    # Aggiungi l'intestazione della tabella
    pdf.set_font("Arial", size=12)
    pdf.set_fill_color(200, 200, 200)
    
    if has_bagni:
        # Layout con colonna pulizia bagni
        pdf.cell(25, 10, 'Giorno', border='LTB', align='R', fill=True)
        pdf.cell(10, 10, ' ', border='RTB', align='C', fill=True)
        pdf.cell(80, 10, 'Luogo', border=1, align='C', fill=True)
        pdf.cell(40, 10, 'Orario', border=1, align='C', fill=True)
        pdf.cell(30, 10, 'Pulizia bagni', border=1, align='C', fill=True)
    else:
        # Layout originale senza colonna pulizia bagni
        pdf.cell(30, 10, 'Giorno', border='LTB', align='R', fill=True)
        pdf.cell(15, 10, ' ', border='RTB', align='C', fill=True)
        pdf.cell(85, 10, 'Luogo', border=1, align='C', fill=True)
        pdf.cell(60, 10, 'Orario', border=1, align='C', fill=True)
    
    pdf.ln()

    # Aggiungi i turni
    for shift in shifts:
        day, day_number, location, time = shift[:4]
        pulizia_bagni = shift[4] if len(shift) > 4 else ""
        
        # Usa la funzione di formattazione per visualizzare "mercoledì" correttamente
        day_display = format_day_for_display(day)
        
        if has_bagni:
            pdf.cell(25, 10, day_display, border='LTB', align='R')
            pdf.cell(10, 10, day_number, border='RTB', align='L')
            pdf.cell(80, 10, location[:40], border=1, align='C')  # Tronca se troppo lungo
            pdf.cell(40, 10, time, border=1, align='C')
            pdf.cell(30, 10, pulizia_bagni, border=1, align='C')
        else:
            pdf.cell(30, 10, day_display, border='LTB', align='R')
            pdf.cell(15, 10, day_number, border='RTB', align='L')
            pdf.cell(85, 10, location[:44], border=1, align='C')
            pdf.cell(60, 10, time, border=1, align='C')
        
        pdf.ln()

    # Salva il PDF
    pdf.output(output_filename)
    print(f"File '{output_filename}' creato con successo!")

def find_pdf_file():
    """Cerca un file PDF che inizia con 'servizio custodia' nella cartella corrente."""
    pattern = os.path.join(os.getcwd(), "*")
    all_files = glob.glob(pattern)
    
    pdf_files = []
    for file in all_files:
        if file.lower().endswith('.pdf'):
            filename = os.path.basename(file).lower()
            if filename.startswith('servizio custodia'):
                pdf_files.append(file)
    
    return pdf_files

def main():
    """Main function."""
    global DEBUG_MODE
    
    # Chiedi all'utente se vuole attivare la modalità debug
    debug_choice = input("Vuoi attivare la modalità debug? (s/n): ").strip().lower()
    DEBUG_MODE = debug_choice in ['s', 'si', 'sì', 'y', 'yes']
    
    if DEBUG_MODE:
        print("Modalità debug attivata.")
    print()
    
    # Cerca automaticamente file PDF che iniziano con "servizio custodia"
    pdf_files = find_pdf_file()
    pdf_path = None
    
    if pdf_files:
        if len(pdf_files) == 1:
            filename = os.path.basename(pdf_files[0])
            conferma = input(f"Trovato file: {filename}\nConfermi? (s/n): ").strip().lower()
            if conferma in ['s', 'si', 'sì', 'y', 'yes']:
                pdf_path = pdf_files[0]
        else:
            print("Trovati più file:")
            for i, file in enumerate(pdf_files, 1):
                print(f"{i}. {os.path.basename(file)}")
            
            while pdf_path is None:
                try:
                    scelta = int(input("Quale file vuoi processare? (numero): ")) - 1
                    if 0 <= scelta < len(pdf_files):
                        pdf_path = pdf_files[scelta]
                    else:
                        print("Scelta non valida. Riprova.")
                except ValueError:
                    print("Input non valido. Riprova.")
    
    if pdf_path is None:
        pdf_path = input("Inserisci il nome del file PDF da processare (inclusa estensione .pdf): ")
    
    surname = input("Inserisci il cognome della persona da cercare: ").strip()
    
    # Read tables from PDF
    tables = read_pdf_tables(pdf_path)
    if tables is None:
        return
    
    # Extract and write the shifts using hardcoded structure
    shifts = extract_shifts_for_person_hardcoded(tables, surname)
    
    if not shifts:
        print(f"\nNessun turno trovato per {surname}")
        return
    
    # Ordinare i turni prima di scrivere nel PDF
    shifts_sorted = sort_days(shifts)
    
    # Chiedi se sono necessarie modifiche
    print_shifts(shifts_sorted)
    
    modifica = input("\nSono necessarie modifiche ai turni? (s/n): ").strip().lower()
    if modifica in ['s', 'si', 'sì', 'y', 'yes']:
        shifts_sorted = modify_shifts(shifts_sorted)
    
    # Scrivi i turni nel file PDF
    write_shifts_to_pdf(shifts_sorted, pdf_path, surname)

    input("Premi Invio per uscire...") 

if __name__ == "__main__":
    main()
