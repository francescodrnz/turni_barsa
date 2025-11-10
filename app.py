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

def display_pdf(pdf_bytes, title="PDF"):
    """Mostra un PDF nel browser usando un iframe"""
    base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf"></iframe>'
    st.markdown(f"### {title}")
    st.markdown(pdf_display, unsafe_allow_html=True)

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
            display_pdf(st.session_state.generated_pdf_bytes, "Anteprima PDF")
            
            st.markdown("---")
            
            # Pulsante download centrato
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.download_button(
                    label="⬇️ Scarica PDF",
                    data=st.session_state.generated_pdf_bytes,
                    file_name=st.session_state.output_filename,
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True
                )
    
    with tab2:
        st.markdown("### ✏️ Modifica Turni")
        
        # Form per aggiungere un nuovo turno
        with st.expander("➕ Aggiungi nuovo turno", expanded=False):
            with st.form(key="add_shift_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    giorni = ['lunedì', 'martedì', 'mercoledì', 'giovedì', 'venerdì', 'sabato', 'domenica']
                    giorno = st.selectbox("Giorno", giorni)
                    luogo = st.text_input("Luogo", placeholder="Es: Giardini del Castello")
                
                with col2:
                    data = st.number_input("Data (giorno del mese)", min_value=1, max_value=31, value=1)
                    orario = st.text_input("Orario (es: 08:00-14:00)", placeholder="08:00-14:00")
                
                # Checkbox per pulizia bagni
                pulizia_bagni_check = st.checkbox("Pulizia bagni (solo per Giardini del Castello)", value=False)
                
                submitted = st.form_submit_button("Aggiungi turno", type="primary")
                
                if submitted:
                    if luogo:
                        giorno_norm = normalize_day_name(giorno)
                        # Determina il valore di pulizia bagni
                        if "giardini del castello" in luogo.lower():
                            pulizia_bagni = "Sì" if pulizia_bagni_check else "No"
                        else:
                            pulizia_bagni = ""
                        
                        nuovo_turno = (giorno_norm, str(data), luogo, orario, pulizia_bagni)
                        st.session_state.shifts.append(nuovo_turno)
                        st.session_state.shifts = sort_days(st.session_state.shifts)
                        st.session_state.need_regenerate = True
                        st.success(f"✅ Turno aggiunto: {giorno} {data} - {luogo} {orario}")
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
                if st.button("💾 Salva e Rigenera PDF", type="secondary", use_container_width=True):
                    st.session_state.need_regenerate = True
                    st.success("✅ Modifiche salvate! Vai alla tab 'PDF Generato' per vedere le modifiche.")
                    st.rerun()
            with col_info:
                st.info("💡 Dopo aver modificato i turni, clicca 'Salva e Rigenera PDF' e torna alla tab 'PDF Generato'")
    
    with tab3:
        if st.session_state.input_pdf_bytes:
            display_pdf(st.session_state.input_pdf_bytes, "PDF di Input")

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