import streamlit as st
from main import (
    parse_pdf,
    extract_shifts_for_person_hardcoded,
    write_shifts_to_pdf,
    sort_days,
    has_giardini_castello,
    format_day_for_display,
    normalize_day_name,
    get_hardcoded_structure,
    structure_to_json_bytes,
    structure_from_json_bytes,
    get_raw_pdf_rows,
)
import tempfile
import os
import re
import pandas as pd
from pdf2image import convert_from_bytes
from PIL import Image, ImageDraw
import io
import fitz  # PyMuPDF

st.set_page_config(page_title="Generatore Turni PDF", page_icon="📅", layout="wide")


# ── Helpers ──────────────────────────────────────────────────────────────────

def get_output_filename(input_filename, surname):
    match = re.search(r"DAL.*\.pdf", input_filename, re.IGNORECASE)
    return f"Turni {surname} " + match.group(0).lower() if match else f"Turni {surname}.pdf"


def display_pdf(pdf_bytes, title=None, filename=None, show_download=False, width_percentage=100, highlight_text=None):
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
                width="stretch"
            )
        st.markdown("---")

    try:
        def normalize_token(s):
            s = s.strip()
            s = re.sub(r"[^\wÀ-ÖØ-öø-ÿ]+", "", s, flags=re.UNICODE)
            return s.lower()

        if not highlight_text or highlight_text.strip() == "":
            with st.spinner("Caricamento anteprima ad alta qualità..."):
                images = convert_from_bytes(pdf_bytes, dpi=300)
            for i, image in enumerate(images):
                if width_percentage < 100:
                    lm = (100 - width_percentage) / 2
                    c1, c2, c3 = st.columns([lm, width_percentage, lm])
                    with c2:
                        st.image(image, width="stretch", caption=f"Pagina {i+1}")
                else:
                    st.image(image, width="stretch", caption=f"Pagina {i+1}")
                if i < len(images) - 1:
                    st.markdown("---")
            return

        target_tokens = [normalize_token(t) for t in highlight_text.strip().split() if normalize_token(t)]
        if not target_tokens:
            images = convert_from_bytes(pdf_bytes, dpi=300)
            for i, image in enumerate(images):
                st.image(image, width="stretch", caption=f"Pagina {i+1}")
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
            pix = page.get_pixmap(matrix=mat, alpha=False)
            mode = "RGB" if pix.n < 4 else "RGBA"
            img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
            overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(overlay)
            words = page.get_text("words")
            found_any = False

            if try_sequence:
                n, m = len(words), len(target_tokens)
                for idx in range(n - m + 1):
                    if all(normalize_token(words[idx + k][4]) == target_tokens[k] for k in range(m)):
                        found_any = True
                        x0 = min(words[idx + k][0] for k in range(m))
                        y0 = min(words[idx + k][1] for k in range(m))
                        x1 = max(words[idx + k][2] for k in range(m))
                        y1 = max(words[idx + k][3] for k in range(m))
                        rect = fitz.Rect(x0, y0, x1, y1) * mat
                        draw.rectangle([rect.x0, rect.y0, rect.x1, rect.y1], fill=(255, 230, 0, 120))

            if not found_any:
                for w in words:
                    if normalize_token(w[4]) == first_token:
                        rect = fitz.Rect(w[0], w[1], w[2], w[3]) * mat
                        draw.rectangle([rect.x0, rect.y0, rect.x1, rect.y1], fill=(255, 230, 0, 120))

            highlighted = Image.alpha_composite(img.convert("RGBA"), overlay)
            if width_percentage < 100:
                lm = (100 - width_percentage) / 2
                c1, c2, c3 = st.columns([lm, width_percentage, lm])
                with c2:
                    st.image(highlighted, width="stretch", caption=f"Pagina {i+1}")
            else:
                st.image(highlighted, width="stretch", caption=f"Pagina {i+1}")
            if i < doc.page_count - 1:
                st.markdown("---")
        doc.close()

    except Exception as e:
        st.error(f"Errore nella visualizzazione del PDF: {str(e)}")
        if show_download:
            st.info("Apri il PDF esternamente per verificare il contenuto.")


def init_session_state():
    defaults = {
        'shifts': None,
        'pdf_processed': False,
        'output_filename': None,
        'input_pdf_bytes': None,
        'input_filename': None,
        'surname': None,
        'generated_pdf_bytes': None,
        'need_regenerate': True,
        'structure': None,  # dict {int: (location, time, notes)}
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def get_structure():
    """Restituisce la struttura attiva (da session_state o default)."""
    if st.session_state.structure is None:
        st.session_state.structure = get_hardcoded_structure()
    return st.session_state.structure


def structure_to_df(structure: dict) -> pd.DataFrame:
    """Converte la struttura in DataFrame per st.data_editor."""
    rows = sorted(structure.items())
    return pd.DataFrame(
        [{"Riga PDF": k, "Luogo": v[0], "Orario": v[1]} for k, v in rows],
        columns=["Riga PDF", "Luogo", "Orario"]
    )


def df_to_structure(df: pd.DataFrame) -> dict:
    """Converte il DataFrame editato nella struttura interna."""
    result = {}
    for _, row in df.iterrows():
        try:
            idx = int(row["Riga PDF"])
            result[idx] = (str(row["Luogo"]), str(row["Orario"]), "")
        except (ValueError, TypeError):
            pass
    return result


def generate_pdf_bytes(shifts, output_filename, surname):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_out:
        tmp_out_path = tmp_out.name
    output_name = write_shifts_to_pdf(shifts, output_filename, surname)
    with open(output_name, "rb") as f:
        pdf_bytes = f.read()
    for p in [output_name, tmp_out_path]:
        if os.path.exists(p):
            os.remove(p)
    return pdf_bytes


# ── App ───────────────────────────────────────────────────────────────────────

init_session_state()

st.title("📅 Generatore Turni in PDF")
st.markdown("---")

col_upload, col_surname = st.columns([2, 1])
with col_upload:
    uploaded_file = st.file_uploader("📁 Carica il PDF dei turni", type="pdf")
with col_surname:
    surname = st.text_input("👤 Cognome", placeholder="Es: Rossi")

if uploaded_file and surname:
    if st.button("🔍 Estrai turni", type="primary") or not st.session_state.pdf_processed:
        with st.spinner("Elaborazione in corso..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(uploaded_file.read())
                tmp_path = tmp.name
            
            # Store path in session state for debug use in Structure tab
            st.session_state.temp_pdf_path = tmp_path

            tables = parse_pdf(tmp_path)
            if tables:
                shifts = extract_shifts_for_person_hardcoded(
                    tables, surname, structure=get_structure()
                )
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

if st.session_state.pdf_processed and st.session_state.shifts:
    st.markdown("---")
    tab1, tab2, tab3, tab4 = st.tabs(["📥 PDF Generato", "✏️ Modifica Turni", "📄 PDF Input", "⚙️ Struttura PDF"])

    # ── Tab 1: PDF Generato ───────────────────────────────────────────────────
    with tab1:
        st.markdown("### 📥 PDF Generato")
        if st.session_state.need_regenerate or st.session_state.generated_pdf_bytes is None:
            with st.spinner("Generazione PDF in corso..."):
                st.session_state.generated_pdf_bytes = generate_pdf_bytes(
                    st.session_state.shifts,
                    st.session_state.output_filename,
                    st.session_state.surname
                )
                st.session_state.need_regenerate = False
        if st.session_state.generated_pdf_bytes:
            display_pdf(
                st.session_state.generated_pdf_bytes,
                filename=st.session_state.output_filename,
                show_download=True,
                width_percentage=70,
            )

    # ── Tab 2: Modifica Turni ─────────────────────────────────────────────────
    with tab2:
        st.markdown("### ✏️ Modifica Turni")

        with st.expander("➕ Aggiungi nuovo turno", expanded=False):
            giorni_disponibili = {}
            for shift in st.session_state.shifts:
                day, day_number = shift[0], shift[1]
                if day not in giorni_disponibili:
                    giorni_disponibili[day] = (format_day_for_display(day), day_number)

            day_order = {'lunedì': 1, 'martedì': 2, "mercoledi'": 3, 'giovedì': 4, 'venerdì': 5, 'sabato': 6, 'domenica': 7}
            giorni_sorted = sorted(giorni_disponibili.items(), key=lambda x: day_order.get(x[0], 8))
            giorni_options = [f"{display} {number}" for day, (display, number) in giorni_sorted]
            giorni_map = {f"{display} {number}": (day, number) for day, (display, number) in giorni_sorted}

            with st.form(key="add_shift_form", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    giorno_selezionato = st.selectbox("Giorno", giorni_options)
                    luogo = st.text_input("Luogo", placeholder="Es: Giardini del Castello")
                with c2:
                    orario = st.text_input("Orario (es: 08:00-14:00)", placeholder="08:00-14:00")
                    pulizia_bagni_check = st.checkbox("Pulizia bagni (solo per Giardini del Castello)", value=False)

                if st.form_submit_button("Aggiungi turno", type="primary", width="stretch"):
                    if luogo:
                        giorno_norm, data = giorni_map[giorno_selezionato]
                        pulizia_bagni = ("Sì" if pulizia_bagni_check else "No") if "giardini del castello" in luogo.lower() else ""
                        st.session_state.shifts.append((giorno_norm, str(data), luogo, orario, pulizia_bagni))
                        st.session_state.shifts = sort_days(st.session_state.shifts)
                        st.session_state.need_regenerate = True
                        st.success(f"✅ Turno aggiunto: {format_day_for_display(giorno_norm)} {data} - {luogo} {orario}")
                        st.rerun()
                    else:
                        st.error("⚠️ Inserisci almeno il luogo del turno")

        st.markdown("---")
        st.markdown(f"### 📋 Lista turni ({len(st.session_state.shifts)} turni)")
        has_bagni = has_giardini_castello(st.session_state.shifts)

        with st.container():
            if has_bagni:
                col_day, col_space, col_loc, col_time, col_bagni = st.columns([2, 0.5, 3, 2, 1.5])
            else:
                col_day, col_space, col_loc, col_time = st.columns([2, 0.5, 3, 2])

            with col_day: st.markdown("**Giorno**")
            with col_loc: st.markdown("**Luogo**")
            with col_time: st.markdown("**Orario**")
            if has_bagni:
                with col_bagni: st.markdown("**Pulizia bagni**")
            st.markdown("---")

            new_shifts = []
            for i, shift in enumerate(st.session_state.shifts):
                day, day_number, location, time = shift[:4]
                pulizia_bagni = shift[4] if len(shift) > 4 else ""
                day_display = format_day_for_display(day)

                if has_bagni:
                    col_day, col_space, col_loc, col_time, col_bagni = st.columns([2, 0.5, 3, 2, 1.5])
                else:
                    col_day, col_space, col_loc, col_time = st.columns([2, 0.5, 3, 2])

                with col_day:
                    st.text_input("Giorno", value=f"{day_display} {day_number}", disabled=True, key=f"day_{i}", label_visibility="collapsed")
                with col_loc:
                    new_location = st.text_input("Luogo", value=location, key=f"loc_{i}", label_visibility="collapsed")
                with col_time:
                    new_time = st.text_input("Orario", value=time, key=f"time_{i}", label_visibility="collapsed")

                if has_bagni:
                    with col_bagni:
                        if "giardini del castello" in new_location.lower():
                            current_index = 1 if pulizia_bagni.lower() == "sì" else 0
                            new_pulizia = st.selectbox("Pulizia", ["No", "Sì"], index=current_index, key=f"bagni_{i}", label_visibility="collapsed")
                        else:
                            new_pulizia = ""
                            st.text("")
                else:
                    new_pulizia = ""

                new_shifts.append((day, day_number, new_location, new_time, new_pulizia))

            st.markdown("---")
            c_save, c_info = st.columns([1, 3])
            with c_save:
                if st.button("💾 Salva e Rigenera PDF", type="secondary", width="stretch"):
                    st.session_state.shifts = new_shifts
                    st.session_state.need_regenerate = True
                    st.success("✅ Modifiche salvate! Vai alla tab 'PDF Generato'.")
                    st.rerun()
            with c_info:
                st.info("💡 Dopo aver modificato i turni, clicca 'Salva e Rigenera PDF' e torna alla tab 'PDF Generato'")

    # ── Tab 3: PDF Input ──────────────────────────────────────────────────────
    with tab3:
        st.markdown("### 📄 Visualizzazione PDF Input")
        st.info("Anteprima del PDF originale con evidenziato il cognome cercato.")

    # ── Tab 4: Struttura PDF ──────────────────────────────────────────────────
    with tab4:
        st.markdown("### ⚙️ Struttura righe PDF")
        st.markdown(
            "Ogni riga corrisponde a una riga della tabella nel PDF sorgente (0-indexed, dopo l'header). "
            "**Riga PDF** è l'indice; i gap tra indici indicano righe vuote/ignorate nel PDF."
        )
        st.markdown("---")
        
        # DEBUG PDF RIGHE
        with st.expander("🔍 Modalità Debug - Visualizza righe grezze dal PDF", expanded=False):
            if hasattr(st.session_state, "temp_pdf_path") and os.path.exists(st.session_state.temp_pdf_path):
                if st.button("🔄 Carica/Aggiorna righe PDF"):
                    raw_data = get_raw_pdf_rows(st.session_state.temp_pdf_path)
                    st.session_state.raw_pdf_rows = raw_data
                
                if hasattr(st.session_state, "raw_pdf_rows"):
                    st.markdown("Questa tabella mostra esattamente cosa legge il PDF per ogni riga.")
                    st.dataframe(st.session_state.raw_pdf_rows, use_container_width=True)
            else:
                st.warning("Carica prima un PDF per vedere le righe grezze.")

        st.markdown("---")

        # Upload JSON
        uploaded_json = st.file_uploader("📂 Carica struttura da JSON", type="json", key="json_uploader")
        if uploaded_json is not None:
            try:
                new_structure = structure_from_json_bytes(uploaded_json.read())
                st.session_state.structure = new_structure
                st.success(f"✅ Struttura caricata: {len(new_structure)} righe definite.")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Errore nel parsing del JSON: {e}")

        st.markdown("---")

        # Editor
        current_structure = get_structure()
        
        # Scalamento righe
        st.markdown("**Gestione righe (scalamento automatico)**")
        col_ins1, col_ins2, col_ins3 = st.columns([1, 1.5, 1.5])
        with col_ins1:
            ins_idx = st.number_input("Indice riga (Riga PDF)", min_value=0, value=0, step=1)
        with col_ins2:
            st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
            if st.button("➕ Inserisci riga qui", use_container_width=True, help="Inserisce una nuova riga all'indice specificato e fa slittare in avanti tutte le successive"):
                new_struct = {}
                for k, v in current_structure.items():
                    if k >= ins_idx:
                        new_struct[k + 1] = v
                    else:
                        new_struct[k] = v
                new_struct[ins_idx] = ("Nuovo Luogo", "", "")
                st.session_state.structure = new_struct
                st.rerun()
        with col_ins3:
            st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
            if st.button("➖ Rimuovi riga qui", use_container_width=True, help="Rimuove la riga all'indice specificato e fa arretrare tutte le successive"):
                if ins_idx in current_structure:
                    new_struct = {}
                    for k, v in current_structure.items():
                        if k < ins_idx:
                            new_struct[k] = v
                        elif k > ins_idx:
                            new_struct[k - 1] = v
                    st.session_state.structure = new_struct
                    st.rerun()
                else:
                    st.warning(f"La riga {ins_idx} non esiste nella struttura.")

        st.markdown("---")

        df = structure_to_df(current_structure)

        st.markdown("**Modifica manuale la struttura** — modifica luogo e orario:")
        edited_df = st.data_editor(
            df,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "Riga PDF": st.column_config.NumberColumn(
                    "Riga PDF",
                    help="Indice 0-based della riga nel PDF sorgente (dopo l'header)",
                    min_value=0,
                    step=1,
                    required=True,
                ),
                "Luogo": st.column_config.TextColumn("Luogo", required=True),
                "Orario": st.column_config.TextColumn("Orario", help="Formato HH:MM-HH:MM, vuoto per Riposo/Ferie"),
            },
            key="structure_editor",
        )

        c_apply, c_download, c_reset = st.columns([1, 1, 1])

        with c_apply:
            if st.button("✅ Applica e Salva", type="primary", width="stretch", help="Applica la struttura e salva sul file locale structure.json"):
                new_structure = df_to_structure(edited_df)
                if new_structure:
                    st.session_state.structure = new_structure
                    # Salva localmente
                    try:
                        with open("structure.json", "wb") as f:
                            f.write(structure_to_json_bytes(new_structure))
                        st.toast("Salvato localmente su structure.json", icon="💾")
                    except Exception as e:
                        st.error(f"Errore salvataggio file: {e}")
                        
                    # Forza la ri-estrazione se c'è già un PDF caricato
                    st.session_state.pdf_processed = False
                    st.session_state.shifts = None
                    
                    # Rimuoviamo i widget temporanei dei turni per forzare il refresh dei valori
                    for key in list(st.session_state.keys()):
                        if key.startswith(("loc_", "time_", "bagni_", "day_")):
                            del st.session_state[key]
                            
                    st.session_state.need_regenerate = True
                    st.success(f"✅ Struttura aggiornata ({len(new_structure)} righe). Ri-estrai i turni.")
                    st.rerun()
                else:
                    st.error("❌ Struttura vuota o non valida.")

        with c_download:
            json_bytes = structure_to_json_bytes(
                df_to_structure(edited_df) if len(edited_df) > 0 else current_structure
            )
            st.download_button(
                label="⬇️ Scarica JSON",
                data=json_bytes,
                file_name="structure.json",
                mime="application/json",
                width="stretch",
            )

        with c_reset:
            if st.button("🔄 Reset a default", type="secondary", width="stretch"):
                st.session_state.structure = get_hardcoded_structure()
                st.session_state.pdf_processed = False
                st.session_state.shifts = None
                st.success("Struttura resettata al default.")
                st.rerun()

        st.markdown("---")
        st.info(
            "**Workflow per PDF aggiornato:** \n"
            "1. Aggiungi/rimuovi righe con i bottoni sopra o modifica i testi nella tabella\n"
            "2. Clicca **Applica e Salva** (salverà sul disco locale se non sei su Cloud)\n"
            "3. Torna in cima, carica il nuovo PDF e clicca **Estrai turni**\n"
            "\n**Nota per la persistenza su Streamlit Cloud:** \n"
            "Le modifiche fatte qui sono temporanee per la sessione se l'app gira su cloud. "
            "Per renderle permanenti su GitHub, clicca **Scarica JSON**, sostituisci il file "
            "`structure.json` nella tua repository locale e fai un nuovo push su GitHub."
        )

# ── Preview PDF Input (Visible on every tab) ──────────────────────────────────
if st.session_state.pdf_processed and st.session_state.input_pdf_bytes:
    st.markdown("---")
    with st.expander("📄 Visualizza PDF Originale (Anteprima)", expanded=True):
        display_pdf(
            st.session_state.input_pdf_bytes,
            highlight_text=st.session_state.surname,
            width_percentage=100,
        )

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666; font-size: 0.8em;'>Generatore Turni PDF v3.1 | Streamlit App</div>",
    unsafe_allow_html=True
)
