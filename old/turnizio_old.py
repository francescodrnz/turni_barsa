import pdfplumber
import os
import re
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from fpdf import FPDF

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

def extract_days(tables):
    """Extract days and their numbers from the table header."""
    days = []
    for table in tables:
        for row in table:
            if row:
                for cell in row:
                    if cell:
                        # Cerca solo giorni nel formato "lunedì 23", "martedì 24", ecc.
                        match = re.match(r"(\w+)\s+(\d+)", cell.strip())
                        if match:
                            giorno = match.group(1).lower()
                            if giorno in ['lunedì', 'martedì', 'mercoledì', 'giovedì', 'venerdì', 'sabato', 'domenica']:
                                #print(f"Giorno estratto: {giorno} - Numero: {match.group(2)}")  # Debug
                                days.append((giorno, match.group(2)))  # Aggiungi giorno e numero
                if days:  # Esci appena trovati i giorni
                    return days
    print("Nessun giorno trovato")  # Debug
    return []
    
def process_table(table):
    """Process table by handling location continuations."""
    processed_table = []
    current_location = None
    current_time = None
    previous_location = None  # Variable to track location continuation

    for row in table:
        if not row or all(cell is None for cell in row):
            continue
            
        processed_row = list(row)  # Create a copy of the row
        
        # Handle location update only if it's not a special case (e.g., "sabato", "domenica")
        if row[0] is not None and not any(c.isdigit() for c in str(row[0])) and ':' not in str(row[0]):
            # Check for special keywords indicating days or holidays
            if any(keyword in row[0].lower() for keyword in ['sabato', 'domenica', 'festivi']):
                current_location = previous_location  # Maintain the previous location
            else:
                location_parts = row[0].split("  ")
                if len(location_parts) > 1:  # If the location contains multiple parts
                    for part in location_parts:
                        if previous_location:
                            current_location = previous_location + " " + part.strip()
                        else:
                            current_location = part.strip()
                        previous_location = current_location  # Update previous location
                else:
                    current_location = row[0].strip().replace("\n", " ")  # Replace newline with space
                    previous_location = current_location  # Store the new location
        elif row[0] is None and previous_location:  # If the current row is empty, continue with previous location
            current_location = previous_location

        processed_row[0] = current_location
        
        # Update time if present (second column)
        if row[1] is not None and ':' in str(row[1]) and '-' in str(row[1]):
            current_time = row[1].strip()
        processed_row[1] = current_time
        
        processed_table.append(processed_row)

    return processed_table
    
def sort_days(shifts):
    """Sort shifts by day of the week and then by time."""
    day_order = {
        'lunedì': 1,
        'martedì': 2,
        'mercoledì': 3,
        'giovedì': 4,
        'venerdì': 5,
        'sabato': 6,
        'domenica': 7
    }

    def get_day_number(shift):
        day = shift[0].split()[0].lower()
        return day_order.get(day, 8)

    def get_time(shift):
        """Extract the time from a shift (if any)."""
        time_str = shift[3]  # Time is now the fourth element (index 3)
        if time_str:
            try:
                # Extract the start time (before the dash)
                start_time = time_str.split('-')[0].strip()
                return datetime.strptime(start_time, "%H:%M")
            except (ValueError, IndexError):
                return datetime.max  # If time is not in correct format, place it at the end
        return datetime.max  # If no time, place it at the end

    def sort_key(shift):
        # Primary sort by day, secondary sort by time
        return (get_day_number(shift), get_time(shift))
    
    # Sort using the composite key function
    return sorted(shifts, key=sort_key)
    
def extract_crudele_shifts(tables, surname):
    """Extract shifts for Crudele."""
    if not tables:
        return []
    
    days = extract_days(tables)
    if not days:
        print("Errore: Non è stato possibile trovare i giorni nelle tabelle")
        return []
    
    # Casi in cui non ci deve essere orario
    no_shift_keywords = ['riposo', 'ferie', 'malattia', 'infortunio', 'permessi vari', 'non lavora']
    
    shifts = []
    processed_days = set()  # Per tracciare i giorni già processati
    
    for table in tables:
        # Process the table to fill in None values
        processed_table = process_table(table)
        
        for row in processed_table:
            if not row:
                continue
                
            location = row[0]
            time_slot = row[1]
            
            if not location:
                continue
            
            # Check for Crudele in each day column
            for col_idx, cell in enumerate(row[2:], 2):  # Start from column 2 (after location and time)
                if cell and surname.lower() in str(cell).lower():
                    day_idx = col_idx - 2  # Adjust index for days list
                    if day_idx < len(days):
                        # Aggiungi il giorno alla lista dei processati
                        day_name, day_number = days[day_idx]
                        processed_days.add(day_name)

                        # Controlliamo se la location contiene una delle parole chiave
                        location_lower = location.lower()  # Convertiamo la location in minuscolo
                        
                        # Se la location contiene una parola chiave, non ci deve essere orario
                        if any(keyword in location_lower for keyword in no_shift_keywords):
                            shifts.append((day_name, day_number, location, ''))  # Nessun orario
                        else:
                            shifts.append((day_name, day_number, location, time_slot))
    
    # Aggiungere giorni mancanti come "Riposo"
    for day_name, day_number in days:
        if day_name not in processed_days:
            shifts.append((day_name, day_number, "Riposo", ""))
    
    return shifts


def write_shifts_to_pdf(shifts, input_filename, surname):
    # Estrai la parte finale del nome del file di input per creare il nome del file di output
    match = re.search(r"DAL.*\.pdf", input_filename)
    if match:
        output_filename = f"Turni {surname} " + match.group(0)[0:]  # Mantieni "DAL" e la parte successiva
    else:
        output_filename = "TURNI.pdf"  # Default se non viene trovata la parte del nome

    # Crea il documento PDF
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Aggiungi il titolo
    pdf.set_font("Arial", "B", size=17)
    pdf.cell(200, 10, txt=f"Turni di lavoro {surname}", ln=True, align='C')  # Titolo con il cognome
    pdf.ln(10)  # Line break

    # Aggiungi l'intestazione della tabella
    pdf.set_font("Arial", size=12)
    pdf.set_fill_color(200, 200, 200)  # Grigio chiaro per lo sfondo
    pdf.cell(30, 10, 'Giorno', border='LTB', align='R', fill=True)
    pdf.cell(20, 10, ' ', border='RTB', align='C', fill=True)
    pdf.cell(80, 10, 'Luogo', border=1, align='C', fill=True)
    pdf.cell(60, 10, 'Orario', border=1, align='C', fill=True)
    pdf.ln()

    # Aggiungi i turni
    for day, day_number, location, time in shifts:
        pdf.cell(30, 10, day, border='LTB', align='R')  # Giorno
        pdf.cell(20, 10, day_number, border='RTB', align='L')  # Numero
        pdf.cell(80, 10, location, border=1, align='C')  # Luogo
        pdf.cell(60, 10, time, border=1, align='C')  # Orario
        pdf.ln()

    # Salva il PDF
    pdf.output(output_filename)
    print(f"File '{output_filename}' creato con successo!")


def main():
    # Chiedi il nome del file da processare
    pdf_path = input("Inserisci il nome del file PDF da processare (inclusa estensione .pdf): ")
    surname = input("Inserisci il cognome della persona da cercare (es. Crudele): ").strip()
    
    # Read tables from PDF
    tables = read_pdf_tables(pdf_path)
    if tables is None:
        return
    
    # Extract and write the shifts
    shifts = extract_crudele_shifts(tables, surname)
    
    if not shifts:
        print("\nNessun turno trovato per", surname)
        return
    
    # Ordinare i turni prima di scrivere nel PDF
    shifts_sorted = sort_days(shifts)
    
    # Scrivi i turni nel file PDF
    write_shifts_to_pdf(shifts_sorted, pdf_path, surname)

    input("Premi Invio per uscire...") 

if __name__ == "__main__":
    main()
