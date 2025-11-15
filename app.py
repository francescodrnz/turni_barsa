import streamlit as st
from main import (
    parse_pdf, 
    extract_shifts_for_person_hardcoded,
    write_shifts_to_pdf,
    sort_days,
    has_giardini_castello,
    format_day_for_display,
    normalize_day_name
)
import tempfile
import os
import re
import base64
from pdf2image import convert_from_bytes
from PIL import Image, ImageDraw
import io
import fitz  # PyMuPDF
import re

# Configurazione pagina
st.set_page_config(
    page_title="Generatore Turni PDF",
    page_icon="📅",
    layout="wide"
)

def get_output_filename(input_filename, surname):
    """Genera il nome del file di output come nel main.py"""
    match = re.search(r"DAL.*\.pdf", input_filename, re.IGNORECASE)
    if match:
        return f"Turni {surname} " + match.group(0).lower()
    else:
        return f"Turni {surname}.pdf"

def display_pdf(pdf_bytes, title=None, filename=None, show_download=False, width_percentage=100, highlight_text=None):
    """Mostra un PDF convertendolo in immagini ed evidenzia highlight_text se presente.
    Se highlight_text contiene più parole, prova prima a evidenziare la sequenza completa;
    se non trova nulla, evidenzia la prima parola."""
    if title:
        st.markdown(f"### {title}")

    if show_download and filename:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.download_button(
                label="⬇️ Scarica PDF",
                data=pdf_bytes,
                file_name=filename,
                mime="application/pdf",
                type="primary",
                use_container_width=True
            )
        st.markdown("---")

    try:
        if not highlight_text or highlight_text.strip() == "":
            with st.spinner("Caricamento anteprima ad alta qualità..."):
                images = convert_from_bytes(pdf_bytes, dpi=300)
            for i, image in enumerate(images):
                if width_percentage < 100:
                    left_margin = (100 - width_percentage) / 2
                    col1, col2, col3 = st.columns([left_margin, width_percentage, left_margin])
                    with col2:
                        st.image(image, use_container_width=True, caption=f"Pagina {i+1}")
                else:
                    st.image(image, use_container_width=True, caption=f"Pagina {i+1}")
                if i < len(images) - 1:
                    st.markdown("---")
            return

        # normalizzazione parola (rimuove punteggiatura ma mantiene lettere accentate)
        def normalize_token(s: str) -> str:
            s = s.strip()
            # rimuove caratteri non alfanumerici (preserva lettere accentate)
            s = re.sub(r"[^\wÀ-ÖØ-öø-ÿ]+", "", s, flags=re.UNICODE)
            return s.lower()

        target_raw = highlight_text.strip()
        target_tokens = [t for t in target_raw.split() if t.strip() != ""]
        target_tokens = [normalize_token(t) for t in target_tokens if normalize_token(t) != ""]

        # se, dopo normalizzazione, non abbiamo token, fallback al comportamento senza highlight
        if not target_tokens:
            with st.spinner("Caricamento anteprima..."):
                images = convert_from_bytes(pdf_bytes, dpi=300)
            for i, image in enumerate(images):
                st.image(image, use_container_width=True, caption=f"Pagina {i+1}")
                if i < len(images) - 1:
                    st.markdown("---")
            return

        first_token = target_tokens[0]
        try_sequence = len(target_tokens) > 1

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        dpi = 300
        mat = fitz.Matrix(dpi / 72.0, dpi / 72.0)

        for i in range(doc.page_count):
            page = doc.load_page(i)

            # Render pagina
            pix = page.get_pixmap(matrix=mat, alpha=False)
            mode = "RGB" if pix.n < 4 else "RGBA"
            img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)

            overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(overlay)

            words = page.get_text("words")  # (x0, y0, x1, y1, "word", ...)

            found_any = False

            if try_sequence:
                # cerca sequenze di parole corrispondenti esattamente a target_tokens
                n = len(words)
                m = len(target_tokens)
                for idx in range(0, n - m + 1):
                    match = True
                    for k in range(m):
                        wtext = normalize_token(words[idx + k][4])
                        if wtext != target_tokens[k]:
                            match = False
                            break
                    if match:
                        found_any = True
                        # unisci bbox della sequenza
                        x0 = min(words[idx + k][0] for k in range(m))
                        y0 = min(words[idx + k][1] for k in range(m))
                        x1 = max(words[idx + k][2] for k in range(m))
                        y1 = max(words[idx + k][3] for k in range(m))
                        rect = fitz.Rect(x0, y0, x1, y1)
                        rect *= mat
                        draw.rectangle([rect.x0, rect.y0, rect.x1, rect.y1], fill=(255, 230, 0, 120))

            if not found_any:
                # fallback: evidenzia tutte le occorrenze della prima parola
                for w in words:
                    wnorm = normalize_token(w[4])
                    if wnorm == first_token:
                        rect = fitz.Rect(w[0], w[1], w[2], w[3])
                        rect *= mat
                        draw.rectangle([rect.x0, rect.y0, rect.x1, rect.y1], fill=(255, 230, 0, 120))

            # composizione immagine + overlay
            img_rgba = img.convert("RGBA")
            highlighted = Image.alpha_composite(img_rgba, overlay)

            # Display
            if width_percentage < 100:
                left_margin = (100 - width_percentage) / 2
                col1, col2, col3 = st.columns([left_margin, width_percentage, left_margin])
                with col2:
                    st.image(highlighted, use_container_width=True, caption=f"Pagina {i+1}")
            else:
                st.image(highlighted, use_container_width=True, caption=f"Pagina {i+1}")

            if i < doc.page_count - 1:
                st.markdown("---")

        doc.close()

    except Exception as e:
        st.error(f"Errore nella visualizzazione del PDF: {str(e)}")
        if show_download:
            st.info("Apri il PDF esternamente per verificare il contenuto.")

def init_session_state():
    """Inizializza lo stato della sessione"""
    if 'shifts' not in st.session_state:
        st.session_state.shifts = None
    if 'pdf_processed' not in st.session_state:
        st.session_state.pdf_processed = False
    if 'output_filename' not in st.session_state:
        st.session_state.output_filename = None
    if 'input_pdf_bytes' not in st.session_state:
        st.session_state.input_pdf_bytes = None
    if 'input_filename' not in st.session_state:
        st.session_state.input_filename = None
    if 'surname' not in st.session_state:
        st.session_state.surname = None
    if 'generated_pdf_bytes' not in st.session_state:
        st.session_state.generated_pdf_bytes = None
    if 'need_regenerate' not in st.session_state:
        st.session_state.need_regenerate = True

def generate_pdf_bytes(shifts, output_filename, surname):
    """Genera il PDF e restituisce i bytes"""
    # Genera il PDF in un file temporaneo
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_out:
        tmp_out_path = tmp_out.name
    
    # Scrivi i turni nel PDF
    output_name = write_shifts_to_pdf(shifts, output_filename, surname)
    
    # Leggi il file generato
    with open(output_name, "rb") as f:
        pdf_bytes = f.read()
    
    # Cleanup
    if os.path.exists(output_name):
        os.remove(output_name)
    if os.path.exists(tmp_out_path):
        os.remove(tmp_out_path)
    
    return pdf_bytes

# Main app
init_session_state()

st.title("📅 Generatore Turni in PDF")
st.markdown("---")

# Upload e input
col_upload, col_surname = st.columns([2, 1])

with col_upload:
    uploaded_file = st.file_uploader("📁 Carica il PDF dei turni", type="pdf")

with col_surname:
    surname = st.text_input("👤 Cognome", placeholder="Es: Rossi")

# Pulsante per elaborare
if uploaded_file and surname:
    if st.button("🔍 Estrai turni", type="primary") or not st.session_state.pdf_processed:
        with st.spinner("Elaborazione in corso..."):
            # Salva il PDF in un file temporaneo
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(uploaded_file.read())
                tmp_path = tmp.name
            
            # Estrai le tabelle
            tables = parse_pdf(tmp_path)
            
            if tables:
                # Estrai i turni
                shifts = extract_shifts_for_person_hardcoded(tables, surname)
                
                if shifts:
                    st.session_state.shifts = sort_days(shifts)
                    st.session_state.pdf_processed = True
                    st.session_state.output_filename = get_output_filename(uploaded_file.name, surname)
                    st.session_state.input_pdf_bytes = uploaded_file.getvalue()
                    st.session_state.input_filename = uploaded_file.name
                    st.session_state.surname = surname
                    st.session_state.need_regenerate = True
                    st.success(f"✅ Trovati {len(shifts)} turni per {surname}")
                    st.rerun()
                else:
                    st.error(f"❌ Nessun turno trovato per {surname}")
                    st.session_state.pdf_processed = False
            else:
                st.error("❌ Errore nella lettura del PDF")
                st.session_state.pdf_processed = False
            
            # Rimuovi il file temporaneo
            os.remove(tmp_path)

# Mostra i turni se elaborati
if st.session_state.pdf_processed and st.session_state.shifts:
    st.markdown("---")
    
    # Tabs - PDF generato come primo tab (default)
    tab1, tab2, tab3 = st.tabs(["📥 PDF Generato", "✏️ Modifica Turni", "📄 PDF Input"])
    
    with tab1:
        st.markdown("### 📥 PDF Generato")
        
        # Genera il PDF se necessario
        if st.session_state.need_regenerate or st.session_state.generated_pdf_bytes is None:
            with st.spinner("Generazione PDF in corso..."):
                st.session_state.generated_pdf_bytes = generate_pdf_bytes(
                    st.session_state.shifts,
                    st.session_state.output_filename,
                    st.session_state.surname
                )
                st.session_state.need_regenerate = False
        
        # Mostra anteprima
        if st.session_state.generated_pdf_bytes:
            display_pdf(
                st.session_state.generated_pdf_bytes,
                title=None,
                filename=st.session_state.output_filename,
                show_download=True,
                width_percentage=70,
                highlight_text=None
            )
    
    with tab2:
        st.markdown("### ✏️ Modifica Turni")
        
        # Form per aggiungere un nuovo turno
        with st.expander("➕ Aggiungi nuovo turno", expanded=False):
            # Estrai i giorni unici con le loro date dai turni esistenti
            giorni_disponibili = {}
            for shift in st.session_state.shifts:
                day, day_number = shift[0], shift[1]
                day_display = format_day_for_display(day)
                if day not in giorni_disponibili:
                    giorni_disponibili[day] = (day_display, day_number)
            
            # Ordina i giorni per ordine settimanale
            day_order = {
                'lunedì': 1, 'martedì': 2, "mercoledi'": 3, 
                'giovedì': 4, 'venerdì': 5, 'sabato': 6, 'domenica': 7
            }
            giorni_sorted = sorted(giorni_disponibili.items(), key=lambda x: day_order.get(x[0], 8))
            
            # Crea le opzioni per il selectbox
            giorni_options = [f"{display} {number}" for day, (display, number) in giorni_sorted]
            giorni_map = {f"{display} {number}": (day, number) for day, (display, number) in giorni_sorted}
            
            with st.form(key="add_shift_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    giorno_selezionato = st.selectbox("Giorno", giorni_options)
                    luogo = st.text_input("Luogo", placeholder="Es: Giardini del Castello")
                
                with col2:
                    orario = st.text_input("Orario (es: 08:00-14:00)", placeholder="08:00-14:00")
                    # Checkbox per pulizia bagni
                    pulizia_bagni_check = st.checkbox("Pulizia bagni (solo per Giardini del Castello)", value=False)
                
                submitted = st.form_submit_button("Aggiungi turno", type="primary", width="stretch")
                
                if submitted:
                    if luogo:
                        # Recupera giorno normalizzato e data dalla mappa
                        giorno_norm, data = giorni_map[giorno_selezionato]
                        
                        # Determina il valore di pulizia bagni
                        if "giardini del castello" in luogo.lower():
                            pulizia_bagni = "Sì" if pulizia_bagni_check else "No"
                        else:
                            pulizia_bagni = ""
                        
                        nuovo_turno = (giorno_norm, str(data), luogo, orario, pulizia_bagni)
                        st.session_state.shifts.append(nuovo_turno)
                        st.session_state.shifts = sort_days(st.session_state.shifts)
                        st.session_state.need_regenerate = True
                        
                        # Mostra il giorno in formato leggibile
                        giorno_display = format_day_for_display(giorno_norm)
                        st.success(f"✅ Turno aggiunto: {giorno_display} {data} - {luogo} {orario}")
                        st.rerun()
                    else:
                        st.error("⚠️ Inserisci almeno il luogo del turno")
        
        st.markdown("---")
        st.markdown(f"### 📋 Lista turni ({len(st.session_state.shifts)} turni)")
        
        # Mostra la lista dei turni in una tabella editabile
        has_bagni = has_giardini_castello(st.session_state.shifts)
        
        # Container per la tabella
        with st.container():
            # Header
            if has_bagni:
                col_day, col_space, col_loc, col_time, col_bagni = st.columns([2, 0.5, 3, 2, 1.5])
            else:
                col_day, col_space, col_loc, col_time = st.columns([2, 0.5, 3, 2])
            
            with col_day:
                st.markdown("**Giorno**")
            with col_loc:
                st.markdown("**Luogo**")
            with col_time:
                st.markdown("**Orario**")
            if has_bagni:
                with col_bagni:
                    st.markdown("**Pulizia bagni**")
            
            st.markdown("---")
            
            # Turni editabili
            modified = False
            for i, shift in enumerate(st.session_state.shifts):
                day, day_number, location, time = shift[:4]
                pulizia_bagni = shift[4] if len(shift) > 4 else ""
                day_display = format_day_for_display(day)
                
                if has_bagni:
                    col_day, col_space, col_loc, col_time, col_bagni = st.columns([2, 0.5, 3, 2, 1.5])
                else:
                    col_day, col_space, col_loc, col_time = st.columns([2, 0.5, 3, 2])
                
                with col_day:
                    st.text_input(
                        "Giorno",
                        value=f"{day_display} {day_number}",
                        disabled=True,
                        key=f"day_{i}",
                        label_visibility="collapsed"
                    )
                
                with col_loc:
                    new_location = st.text_input(
                        "Luogo",
                        value=location,
                        key=f"loc_{i}",
                        label_visibility="collapsed"
                    )
                    if new_location != location:
                        modified = True
                
                with col_time:
                    new_time = st.text_input(
                        "Orario",
                        value=time,
                        key=f"time_{i}",
                        label_visibility="collapsed"
                    )
                    if new_time != time:
                        modified = True
                
                if has_bagni:
                    with col_bagni:
                        if "giardini del castello" in new_location.lower():
                            current_index = 0 if pulizia_bagni.lower() != "sì" else 1
                            new_pulizia = st.selectbox(
                                "Pulizia",
                                ["No", "Sì"],
                                index=current_index,
                                key=f"bagni_{i}",
                                label_visibility="collapsed"
                            )
                            if new_pulizia != pulizia_bagni:
                                modified = True
                        else:
                            new_pulizia = ""
                            st.text("")  # Spacer
                else:
                    new_pulizia = ""
                
                # Aggiorna il turno se modificato
                if modified:
                    st.session_state.shifts[i] = (day, day_number, new_location, new_time, new_pulizia)
            
            st.markdown("---")
            
            # Pulsante per salvare e rigenerare
            col_save, col_info = st.columns([1, 3])
            with col_save:
                if st.button("💾 Salva e Rigenera PDF", type="secondary", width="stretch"):
                    st.session_state.need_regenerate = True
                    st.success("✅ Modifiche salvate! Vai alla tab 'PDF Generato' per vedere le modifiche.")
                    st.rerun()
            with col_info:
                st.info("💡 Dopo aver modificato i turni, clicca 'Salva e Rigenera PDF' e torna alla tab 'PDF Generato'")
    
    with tab3:
        if st.session_state.input_pdf_bytes:
            display_pdf(
                st.session_state.input_pdf_bytes,
                title=None,
                filename=None,
                show_download=False,
                width_percentage=100,
                highlight_text=st.session_state.surname
            )

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; font-size: 0.8em;'>
    Generatore Turni PDF v2.0 | Streamlit App
    </div>
    """,
    unsafe_allow_html=True
)