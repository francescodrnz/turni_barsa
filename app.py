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
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>'
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

def render_shifts_table(shifts, key_prefix=""):
    """Renderizza la tabella dei turni con possibilità di modifica"""
    has_bagni = has_giardini_castello(shifts)
    
    st.markdown("### 📋 Turni estratti")
    
    # Crea una tabella editabile
    edited_shifts = []
    
    for i, shift in enumerate(shifts):
        day, day_number, location, time = shift[:4]
        pulizia_bagni = shift[4] if len(shift) > 4 else ""
        day_display = format_day_for_display(day)
        
        col1, col2, col3, col4 = st.columns([2, 1, 3, 2])
        
        with col1:
            st.text_input(
                "Giorno",
                value=f"{day_display} {day_number}",
                disabled=True,
                key=f"{key_prefix}_day_{i}",
                label_visibility="collapsed"
            )
        
        with col2:
            # Spacer
            st.write("")
        
        with col3:
            new_location = st.text_input(
                "Luogo",
                value=location,
                key=f"{key_prefix}_loc_{i}",
                label_visibility="collapsed"
            )
        
        with col4:
            new_time = st.text_input(
                "Orario",
                value=time,
                key=f"{key_prefix}_time_{i}",
                label_visibility="collapsed"
            )
        
        # Aggiungi campo pulizia bagni se necessario
        new_pulizia = ""
        if has_bagni and "giardini del castello" in new_location.lower():
            col_bagni1, col_bagni2 = st.columns([3, 2])
            with col_bagni2:
                new_pulizia = st.selectbox(
                    "Pulizia bagni",
                    ["No", "Sì"],
                    index=0 if pulizia_bagni.lower() != "sì" else 1,
                    key=f"{key_prefix}_bagni_{i}",
                    label_visibility="collapsed"
                )
        elif has_bagni:
            new_pulizia = pulizia_bagni
        
        edited_shifts.append((day, day_number, new_location, new_time, new_pulizia))
    
    return edited_shifts

def add_shift_form():
    """Form per aggiungere un nuovo turno"""
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
            
            # Checkbox per pulizia bagni (visibile sempre ma rilevante solo per Giardini del Castello)
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
                    st.success(f"✅ Turno aggiunto: {giorno} {data} - {luogo} {orario}")
                    st.rerun()
                else:
                    st.error("⚠️ Inserisci almeno il luogo del turno")

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
                    st.success(f"✅ Trovati {len(shifts)} turni per {surname}")
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
    
    # Tabs per organizzare meglio
    tab1, tab2, tab3 = st.tabs(["✏️ Modifica Turni", "📄 PDF Input", "📥 Genera PDF"])
    
    with tab1:
        # Aggiungi nuovo turno
        add_shift_form()
        
        st.markdown("---")
        st.markdown(f"### 📋 Turni estratti ({len(st.session_state.shifts)} turni)")
        
        # Mostra e modifica turni esistenti
        edited_shifts = render_shifts_table(st.session_state.shifts, key_prefix="edit")
        
        col_save, col_info = st.columns([1, 3])
        with col_save:
            if st.button("💾 Salva modifiche", type="secondary", use_container_width=True):
                st.session_state.shifts = edited_shifts
                st.success("✅ Modifiche salvate!")
                st.rerun()
        with col_info:
            st.info("💡 Modifica i campi sopra e clicca 'Salva modifiche' per applicare le modifiche")
    
    with tab2:
        if st.session_state.input_pdf_bytes:
            display_pdf(st.session_state.input_pdf_bytes, "PDF di Input")
    
    with tab3:
        st.markdown("### 📥 Scarica il PDF generato")
        
        col_preview, col_download = st.columns([3, 1])
        
        with col_download:
            if st.button("🔨 Genera PDF", type="primary"):
                with st.spinner("Generazione PDF..."):
                    # Genera il PDF
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_out:
                        tmp_out_path = tmp_out.name
                    
                    # Scrivi i turni nel PDF
                    write_shifts_to_pdf(
                        st.session_state.shifts,
                        st.session_state.output_filename,  # usa solo per il pattern del nome
                        surname
                    )
                    
                    # Leggi il file generato
                    output_name = st.session_state.output_filename
                    with open(output_name, "rb") as f:
                        pdf_bytes = f.read()
                    
                    # Mostra pulsante download
                    st.download_button(
                        label="⬇️ Scarica PDF",
                        data=pdf_bytes,
                        file_name=output_name,
                        mime="application/pdf",
                        type="primary"
                    )
                    
                    # Mostra anteprima
                    with col_preview:
                        display_pdf(pdf_bytes, "Anteprima PDF Generato")
                    
                    # Cleanup
                    if os.path.exists(output_name):
                        os.remove(output_name)
                    if os.path.exists(tmp_out_path):
                        os.remove(tmp_out_path)

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