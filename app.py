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
import base64
from pdf2image import convert_from_bytes
from PIL import Image, ImageDraw
import io
import fitz  # PyMuPDF

# ── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Turnizio Bar.S.A.", 
    page_icon="📅", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Custom CSS for Professional Dark Look ─────────────────────────────────────
st.markdown("""
    <style>
    /* Dark Theme Core */
    .stApp {
        background-color: #0f172a;
        color: #f8fafc;
    }
    
    /* Global Text visibility */
    h1, h2, h3, h4, p, label, .stMarkdown {
        color: #f8fafc !important;
    }
    
    /* Headers specific */
    h1 {
        font-weight: 800;
        letter-spacing: -0.02em;
        margin-bottom: 1.5rem !important;
        text-shadow: 0 2px 4px rgba(0,0,0,0.3);
    }
    
    /* Sidebar styling - Dark Slate */
    section[data-testid="stSidebar"] {
        background-color: #1e293b !important;
        border-right: 1px solid #334155;
    }
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p, 
    section[data-testid="stSidebar"] label {
        color: #f8fafc !important;
        font-weight: 500;
    }
    
    /* Tabs styling - Modern Dark */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #1e293b;
        padding: 8px;
        border-radius: 12px;
        border: 1px solid #334155;
    }
    .stTabs [data-baseweb="tab"] {
        height: 48px;
        border-radius: 8px;
        border: none;
        padding: 0px 24px;
        color: #94a3b8;
        background-color: transparent;
        transition: all 0.2s ease-in-out;
    }
    .stTabs [data-baseweb="tab"]:hover {
        background-color: #334155;
        color: #f8fafc;
    }
    .stTabs [aria-selected="true"] {
        background-color: #3b82f6 !important;
        color: #ffffff !important;
        box-shadow: 0 4px 12px -2px rgba(59, 130, 246, 0.4);
        font-weight: 700;
    }
    
    /* Expanders & Forms - Dark Cards */
    div[data-testid="stExpander"], .stForm {
        border: 1px solid #334155 !important;
        border-radius: 12px !important;
        background-color: #1e293b !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    }
    div[data-testid="stExpander"] details summary {
        color: #f8fafc !important;
        font-weight: 600 !important;
        background-color: #1e293b;
        padding: 12px 16px;
        border-radius: 12px;
    }
    
    /* Widget Inputs - High Contrast Dark */
    .stTextInput input, .stSelectbox div[data-baseweb="select"], .stNumberInput input {
        background-color: #334155 !important;
        color: #f8fafc !important;
        border: 1px solid #475569 !important;
    }
    
    /* Data Editor Theme override */
    div[data-testid="stDataEditor"] {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 10px;
    }
    
    /* Buttons */
    .stButton>button {
        border-radius: 8px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .stButton>button[kind="primary"] {
        background-color: #3b82f6;
        border: none;
    }
    .stButton>button[kind="primary"]:hover {
        background-color: #2563eb;
        transform: translateY(-1px);
    }
    
    /* Zoomable Container */
    .zoom-container {
        height: 600px;
        overflow: auto;
        border: 2px solid #334155;
        border-radius: 12px;
        background-color: #0f172a;
        cursor: grab;
    }
    .zoom-container:active {
        cursor: grabbing;
    }
    
    /* Footer */
    .footer {
        text-align: center;
        color: #94a3b8;
        font-size: 0.85rem;
        margin-top: 4rem;
        padding: 2rem 0;
        border-top: 1px solid #334155;
        background-color: #0f172a;
    }
    </style>
    """, unsafe_allow_html=True)


# ── Helpers ──────────────────────────────────────────────────────────────────

def get_output_filename(input_filename, surname):
    match = re.search(r"DAL.*\.pdf", input_filename, re.IGNORECASE)
    return f"Turni {surname} " + match.group(0).lower() if match else f"Turni {surname}.pdf"


def display_pdf(pdf_bytes, title=None, filename=None, show_download=False, highlight_text=None, use_zoom=False):
    if title:
        st.markdown(f"### {title}")

    if show_download and filename:
        c1, c2, c3 = st.columns([1, 1, 1])
        with c2:
            st.download_button(
                label="⬇️ SCARICA PDF GENERATO",
                data=pdf_bytes,
                file_name=filename,
                mime="application/pdf",
                type="primary",
                use_container_width=True
            )
        st.markdown("---")

    # Zoom Controller - Only show slider if use_zoom is True
    if use_zoom:
        zoom_val = st.slider("Livello Zoom (%)", 100, 400, 100, step=10, key=f"zoom_{hash(pdf_bytes)}")
    else:
        zoom_val = 100

    try:
        def normalize_token(s):
            s = s.strip()
            s = re.sub(r"[^\wÀ-ÖØ-öø-ÿ]+", "", s, flags=re.UNICODE)
            return s.lower()

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        # Use 200 DPI for generated PDF to keep it sharp, 150 for input PDF (standard/zoom)
        dpi = 150 if use_zoom else 200 
        mat = fitz.Matrix(dpi / 72.0, dpi / 72.0)
        
        target_tokens = []
        if highlight_text:
            target_tokens = [normalize_token(t) for t in highlight_text.strip().split() if normalize_token(t)]

        html_images = []
        for i in range(doc.page_count):
            page = doc.load_page(i)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            mode = "RGB" if pix.n < 4 else "RGBA"
            img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
            
            if target_tokens:
                overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))
                draw = ImageDraw.Draw(overlay)
                words = page.get_text("words")
                found_any = False
                
                first_token = target_tokens[0]
                n, m = len(words), len(target_tokens)
                for idx in range(n - m + 1):
                    if all(normalize_token(words[idx + k][4]) == target_tokens[k] for k in range(m)):
                        found_any = True
                        x0 = min(words[idx + k][0] for k in range(m))
                        y0 = min(words[idx + k][1] for k in range(m))
                        x1 = max(words[idx + k][2] for k in range(m))
                        y1 = max(words[idx + k][3] for k in range(m))
                        rect = fitz.Rect(x0, y0, x1, y1) * mat
                        draw.rectangle([rect.x0, rect.y0, rect.x1, rect.y1], fill=(255, 230, 0, 150))

                if not found_any:
                    for w in words:
                        if normalize_token(w[4]) == first_token:
                            rect = fitz.Rect(w[0], w[1], w[2], w[3]) * mat
                            draw.rectangle([rect.x0, rect.y0, rect.x1, rect.y1], fill=(255, 230, 0, 150))
                
                img = Image.alpha_composite(img.convert("RGBA"), overlay)

            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            html_images.append(f'<img src="data:image/png;base64,{img_str}" style="width:100%; margin-bottom:10px; border-radius:4px; display:block;">')
        
        doc.close()
        
        # Wrapping in a scaling div to force horizontal scroll in zoom-container
        # Both PDFs now use the same scrollable container style
        st.markdown(f"""
            <div class="zoom-container">
                <div style="width: {zoom_val}%; min-width: 100%; margin: 0 auto;">
                    {''.join(html_images)}
                </div>
            </div>
        """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Errore visualizzazione PDF: {str(e)}")


def init_session_state():
    defaults = {
        'shifts': None,
        'pdf_processed': False,
        'output_filename': None,
        'input_pdf_bytes': None,
        'surname': None,
        'generated_pdf_bytes': None,
        'need_regenerate': True,
        'structure': None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def get_structure():
    if st.session_state.structure is None:
        st.session_state.structure = get_hardcoded_structure()
    return st.session_state.structure


def structure_to_df(structure: dict) -> pd.DataFrame:
    rows = sorted(structure.items())
    return pd.DataFrame(
        [{"Indice": k, "Luogo": v[0], "Orario": v[1]} for k, v in rows],
        columns=["Indice", "Luogo", "Orario"]
    )


def df_to_structure(df: pd.DataFrame) -> dict:
    result = {}
    for _, row in df.iterrows():
        try:
            idx = int(row["Indice"])
            result[idx] = (str(row["Luogo"]), str(row["Orario"]), "")
        except: pass
    return result


def shifts_to_df(shifts):
    data = []
    for s in shifts:
        data.append({
            "Giorno": format_day_for_display(s[0]),
            "Data": s[1],
            "Luogo": s[2],
            "Orario": s[3],
            "Pulizia Bagni": s[4] if len(s) > 4 else ""
        })
    return pd.DataFrame(data)


def df_to_shifts(df):
    shifts = []
    for _, row in df.iterrows():
        day_norm = normalize_day_name(row["Giorno"])
        shifts.append((day_norm, str(row["Data"]), row["Luogo"], row["Orario"], row["Pulizia Bagni"]))
    return shifts


def generate_pdf_bytes(shifts, output_filename, surname):
    output_name = write_shifts_to_pdf(shifts, output_filename, surname)
    with open(output_name, "rb") as f:
        pdf_bytes = f.read()
    if os.path.exists(output_name):
        os.remove(output_name)
    return pdf_bytes


# ── App Logic ────────────────────────────────────────────────────────────────

init_session_state()

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://www.barsa.it/wp-content/uploads/2019/12/logo-barsa-2.png", width=180)
    st.markdown("### 📥 Caricamento")
    uploaded_file = st.file_uploader("Scegli il PDF dei turni", type="pdf", label_visibility="collapsed")
    surname_input = st.text_input("Cognome da cercare", placeholder="Es: Rossi", value=st.session_state.surname if st.session_state.surname else "Crudele Francesco")
    
    st.markdown("---")
    if st.button("🚀 GENERA TURNI", type="primary", use_container_width=True, disabled=not (uploaded_file and surname_input)):
        with st.spinner("Estrazione dati..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(uploaded_file.read())
                tmp_path = tmp.name
            
            st.session_state.temp_pdf_path = tmp_path
            tables = parse_pdf(tmp_path)
            if tables:
                extracted = extract_shifts_for_person_hardcoded(
                    tables, surname_input, structure=get_structure()
                )
                if extracted:
                    st.session_state.shifts = sort_days(extracted)
                    st.session_state.pdf_processed = True
                    st.session_state.output_filename = get_output_filename(uploaded_file.name, surname_input)
                    st.session_state.input_pdf_bytes = uploaded_file.getvalue()
                    st.session_state.surname = surname_input
                    st.session_state.need_regenerate = True
                    st.toast(f"Trovati {len(extracted)} turni!", icon="✅")
                else:
                    st.error(f"Nessun turno trovato per {surname_input}")
            else:
                st.error("Errore nella lettura del PDF")

    if st.session_state.pdf_processed:
        st.markdown("---")
        st.caption(f"📁 File: {uploaded_file.name if uploaded_file else '-'}")
        st.caption(f"👤 Persona: {st.session_state.surname}")

# ── Main Area ────────────────────────────────────────────────────────────────
st.title("📅 Turnizio Bar.S.A.")

if not st.session_state.pdf_processed:
    st.info("👋 Benvenuto! Carica il PDF dei turni nella barra laterale a sinistra per iniziare.")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        ### Come usare l'app:
        1. **Carica** il file PDF ufficiale.
        2. **Inserisci** il tuo cognome.
        3. **Clicca** su Genera Turni.
        4. **Verifica** e scarica il tuo PDF pulito!
        """)
    with col2:
        st.image("https://cdn-icons-png.flaticon.com/512/3394/3394866.png", width=200)

else:
    tab1, tab2, tab3 = st.tabs(["📄 PDF GENERATO", "✏️ MODIFICA TURNI", "⚙️ CONFIGURAZIONE"])

    # ── TAB 1: PDF GENERATO ──────────────────────────────────────────────────
    with tab1:
        if st.session_state.need_regenerate or st.session_state.generated_pdf_bytes is None:
            with st.spinner("Generazione file..."):
                st.session_state.generated_pdf_bytes = generate_pdf_bytes(
                    st.session_state.shifts,
                    st.session_state.output_filename,
                    st.session_state.surname
                )
                st.session_state.need_regenerate = False
        
        display_pdf(
            st.session_state.generated_pdf_bytes,
            filename=st.session_state.output_filename,
            show_download=True
        )

    # ── TAB 2: MODIFICA TURNI ────────────────────────────────────────────────
    with tab2:
        st.subheader("📋 Gestione Turni Estratti")
        
        # Add new shift form (Compact)
        with st.expander("➕ Aggiungi un nuovo turno manualmente", expanded=False):
            with st.form("new_shift_form", clear_on_submit=True):
                c1, c2, c3 = st.columns([1, 1, 1])
                with c1:
                    d_day = st.selectbox("Giorno", ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"])
                    d_num = st.text_input("Data (Giorno)", placeholder="Es: 15")
                with c2:
                    d_loc = st.text_input("Luogo", placeholder="Es: Giardini del Castello")
                    d_time = st.text_input("Orario", placeholder="Es: 08:00-14:00")
                with c3:
                    st.write("") # Spacer
                    st.write("")
                    d_pul = st.checkbox("Pulizia Bagni")
                    add_btn = st.form_submit_button("AGGIUNGI ORA", use_container_width=True)
                
                if add_btn:
                    if d_loc:
                        new_s = (normalize_day_name(d_day), d_num, d_loc, d_time, "Sì" if d_pul else "No")
                        st.session_state.shifts.append(new_s)
                        st.session_state.shifts = sort_days(st.session_state.shifts)
                        st.session_state.need_regenerate = True
                        st.rerun()
        
        st.markdown("#### Tabella Modifica Rapida")
        st.caption("Puoi modificare i testi direttamente nella tabella qui sotto. Ricordati di cliccare Salva.")
        
        # Shift data editor (Compact & Modern)
        edited_shifts_df = st.data_editor(
            shifts_to_df(st.session_state.shifts),
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "Giorno": st.column_config.SelectboxColumn("Giorno", options=["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"], required=True),
                "Data": st.column_config.TextColumn("Data", width="small"),
                "Luogo": st.column_config.TextColumn("Luogo", width="large"),
                "Orario": st.column_config.TextColumn("Orario", width="medium"),
                "Pulizia Bagni": st.column_config.SelectboxColumn("Pulizia", options=["", "No", "Sì"], width="small"),
            }
        )
        
        c_save, c_empty = st.columns([1, 2])
        with c_save:
            if st.button("💾 SALVA MODIFICHE E RIGENERA PDF", use_container_width=True, type="primary"):
                st.session_state.shifts = df_to_shifts(edited_shifts_df)
                st.session_state.need_regenerate = True
                st.success("Modifiche salvate con successo!")
                st.rerun()

    # ── TAB 3: CONFIGURAZIONE ────────────────────────────────────────────────
    with tab3:
        st.subheader("⚙️ Configurazione Tecnica")
        
        with st.expander("🔍 Strumenti Debug PDF", expanded=False):
            st.write("Visualizza esattamente come il programma legge le righe del PDF per correggere la struttura.")
            if hasattr(st.session_state, "temp_pdf_path") and os.path.exists(st.session_state.temp_pdf_path):
                if st.button("Analizza Righe PDF"):
                    st.session_state.raw_pdf_rows = get_raw_pdf_rows(st.session_state.temp_pdf_path)
                
                if hasattr(st.session_state, "raw_pdf_rows"):
                    st.dataframe(st.session_state.raw_pdf_rows, use_container_width=True, height=300)
            else:
                st.warning("Carica un PDF per attivare il debug.")

        st.markdown("---")
        
        # Structure Table
        st.markdown("#### Mappatura Indici PDF")
        st.caption("Definisce quale Luogo/Orario assegnare in base alla riga in cui viene trovato il cognome.")
        
        col_ed1, col_ed2 = st.columns([2, 1])
        with col_ed1:
            edited_struct_df = st.data_editor(
                structure_to_df(get_structure()),
                num_rows="dynamic",
                use_container_width=True,
                height=400,
                column_config={
                    "Indice": st.column_config.NumberColumn("Indice Riga", disabled=False),
                    "Luogo": st.column_config.TextColumn("Luogo Predefinito"),
                    "Orario": st.column_config.TextColumn("Orario Predefinito"),
                }
            )
        
        with col_ed2:
            st.markdown("##### 🛠️ Azioni Rapide")
            ins_idx = st.number_input("Indice di riferimento", min_value=0, value=0)
            if st.button("➕ Inserisci riga qui", use_container_width=True):
                curr = get_structure()
                new_s = {}
                for k, v in curr.items():
                    if k >= ins_idx: new_s[k+1] = v
                    else: new_s[k] = v
                new_s[ins_idx] = ("Nuovo Luogo", "", "")
                st.session_state.structure = new_s
                st.rerun()
                
            if st.button("➖ Rimuovi riga qui", use_container_width=True):
                curr = get_structure()
                if ins_idx in curr:
                    new_s = {}
                    for k, v in curr.items():
                        if k < ins_idx: new_s[k] = v
                        elif k > ins_idx: new_s[k-1] = v
                    st.session_state.structure = new_s
                    st.rerun()

            st.markdown("---")
            if st.button("💾 APPLICA E SALVA", type="primary", use_container_width=True):
                st.session_state.structure = df_to_structure(edited_struct_df)
                try:
                    with open("structure.json", "wb") as f:
                        f.write(structure_to_json_bytes(st.session_state.structure))
                    st.success("Struttura salvata localmente!")
                except: st.error("Impossibile salvare il file.")
                st.session_state.pdf_processed = False
                st.rerun()
                
            if st.button("🔄 Ripristina Default", use_container_width=True):
                st.session_state.structure = get_hardcoded_structure()
                st.session_state.pdf_processed = False
                st.rerun()

        st.markdown("---")
        st.markdown("#### 📂 Import/Export Struttura")
        c1, c2 = st.columns(2)
        with c1:
            up_json = st.file_uploader("Carica structure.json", type="json")
            if up_json:
                st.session_state.structure = structure_from_json_bytes(up_json.read())
                st.success("JSON caricato!")
                st.rerun()
        with c2:
            st.write("") # Spacer
            st.write("")
            st.download_button(
                "⬇️ Scarica JSON per GitHub",
                data=structure_to_json_bytes(get_structure()),
                file_name="structure.json",
                mime="application/json",
                use_container_width=True
            )

    # ── PDF Input Preview (Bottom) ───────────────────────────────────────────
    st.markdown("---")
    with st.expander("📄 Visualizza PDF Originale (Input)", expanded=False):
        display_pdf(
            st.session_state.input_pdf_bytes,
            highlight_text=st.session_state.surname,
            use_zoom=True
        )

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown(
    "<div class='footer'>Turnizio Bar.S.A. v4.2 | Realizzato per efficienza e precisione</div>",
    unsafe_allow_html=True
)
