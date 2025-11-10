import streamlit as st
import tempfile, os, base64
from main import (
    parse_pdf,
    extract_shifts_for_person_hardcoded,
    sort_days,
    write_shifts_to_pdf,
    format_day_for_display,
    normalize_day_name
)

st.set_page_config(page_title="Generatore Turni in PDF")
st.title("Generatore Turni in PDF")

DAYS_DISPLAY = ['lunedì','martedì','mercoledì','giovedì','venerdì','sabato','domenica']

def shifts_to_dicts(shifts):
    """Trasforma lista di tuple in lista di dict per editing."""
    out = []
    for s in shifts:
        # s expected: (day_internal, day_number, location, time, [pulizia])
        day_internal = s[0]
        day_display = format_day_for_display(day_internal)
        day_number = s[1]
        location = s[2]
        time = s[3] if len(s) > 3 else ""
        pulizia = s[4] if len(s) > 4 else ""
        out.append({
            "day_display": day_display,
            "day_internal": day_internal,
            "date": day_number,
            "location": location,
            "time": time,
            "pulizia": pulizia
        })
    return out

def dicts_to_shifts(dicts):
    """Trasforma dicts modificati in lista di tuple per write_shifts_to_pdf."""
    out = []
    for d in dicts:
        # normalize day back to internal representation
        day_internal = normalize_day_name(d.get("day_display", d.get("day_internal", "")))
        date = d.get("date", "")
        location = d.get("location", "")
        time = d.get("time", "")
        pulizia = d.get("pulizia", "")
        # keep same tuple shape as main expects
        out.append((day_internal, date, location, time, pulizia))
    return out

# uploader + cognome
uploaded_file = st.file_uploader("Carica il PDF dei turni", type="pdf")
surname = st.text_input("Cognome")

# init session state
if "raw_tables" not in st.session_state:
    st.session_state["raw_tables"] = None
if "editable_rows" not in st.session_state:
    st.session_state["editable_rows"] = []
if "tmp_input_path" not in st.session_state:
    st.session_state["tmp_input_path"] = None
if "pdf_bytes" not in st.session_state:
    st.session_state["pdf_bytes"] = None
if "output_name" not in st.session_state:
    st.session_state["output_name"] = None

col1, col2 = st.columns([1,1])
with col1:
    if st.button("Estrai turni") and uploaded_file and surname:
        # salva temporaneo
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded_file.read())
            tmp_path = tmp.name
        st.session_state["tmp_input_path"] = tmp_path

        # parse -> tables -> extract shifts -> sort -> dicts
        tables = parse_pdf(tmp_path)
        st.session_state["raw_tables"] = tables
        shifts = []
        if tables:
            shifts = extract_shifts_for_person_hardcoded(tables, surname)
        shifts = sort_days(shifts)
        st.session_state["editable_rows"] = shifts_to_dicts(shifts)
        st.success(f"Estratti {len(st.session_state['editable_rows'])} righe. Modifica e poi genera il PDF.")
with col2:
    if st.button("Reset estrazione"):
        # pulizia
        if st.session_state.get("tmp_input_path"):
            try:
                os.remove(st.session_state["tmp_input_path"])
            except Exception:
                pass
        st.session_state["raw_tables"] = None
        st.session_state["editable_rows"] = []
        st.session_state["tmp_input_path"] = None
        st.session_state["pdf_bytes"] = None
        st.session_state["output_name"] = None
        st.info("Stato resettato.")

st.markdown("---")

# Editing UI
rows = st.session_state.get("editable_rows", [])
if rows:
    st.write("Modifica i turni (le modifiche vengono applicate premendo 'Salva modifiche'):")
    new_rows = []
    has_bagni = any("giardini del castello" in (r.get("location","") or "").lower() for r in rows)

    for i, r in enumerate(rows):
        cols = st.columns([1, 1, 3, 2, 1])
        # Giorno (select per evitare refusi)
        day_sel = cols[0].selectbox(f"Giorno #{i+1}", options=DAYS_DISPLAY, index=DAYS_DISPLAY.index(r.get("day_display","lunedì")), key=f"day_{i}")
        date_in = cols[1].text_input(f"Data #{i+1}", value=str(r.get("date","")), key=f"date_{i}")
        loc_in = cols[2].text_input(f"Luogo #{i+1}", value=r.get("location",""), key=f"loc_{i}")
        time_in = cols[3].text_input(f"Orario #{i+1}", value=r.get("time",""), key=f"time_{i}")
        if has_bagni or "giardini del castello" in (loc_in or "").lower():
            pulizia_in = cols[4].selectbox(f"Bagni #{i+1}", options=["","Sì","No"], index=(0 if not r.get("pulizia") else (1 if r.get("pulizia").lower()=="sì" or r.get("pulizia").lower()=="si" else 2)), key=f"pul_{i}")
        else:
            pulizia_in = cols[4].text_input(f"Pulizia #{i+1}", value=r.get("pulizia",""), key=f"pul_{i}")

        # Elimina riga
        delete = st.button("Elimina", key=f"del_{i}")
        if delete:
            # mark row for deletion by skipping append
            st.session_state["editable_rows"].pop(i)
            st.experimental_rerun()

        new_rows.append({
            "day_display": day_sel,
            "day_internal": r.get("day_internal", normalize_day_name(day_sel)),
            "date": date_in,
            "location": loc_in,
            "time": time_in,
            "pulizia": pulizia_in or ""
        })

    # aggiungi riga vuota
    if st.button("Aggiungi riga vuota"):
        new_rows.append({
            "day_display": "lunedì",
            "day_internal": "lunedì",
            "date": "",
            "location": "",
            "time": "",
            "pulizia": ""
        })
        st.session_state["editable_rows"] = new_rows
        st.experimental_rerun()

    # Salva modifiche
    if st.button("Salva modifiche"):
        # normalize store
        st.session_state["editable_rows"] = new_rows
        st.success("Modifiche salvate in sessione.")
else:
    st.info("Nessun turno estratto. Carica un PDF e premi 'Estrai turni'.")

st.markdown("---")

# Generate + download
if st.button("Genera PDF"):
    # prepara la lista di tuple e chiama writer
    dicts = st.session_state.get("editable_rows", [])
    if not dicts:
        st.warning("Nessuna riga da generare.")
    else:
        shifts_for_write = dicts_to_shifts(dicts)
        # write_shifts_to_pdf accetta anche la lista di turni direttamente
        write_shifts_to_pdf(shifts_for_write, st.session_state.get("tmp_input_path","input.pdf"), surname)
        output_name = f"Turni {surname}.pdf"
        try:
            with open(output_name, "rb") as f:
                pdf_bytes = f.read()
            st.session_state["pdf_bytes"] = pdf_bytes
            st.session_state["output_name"] = output_name
            st.success("PDF generato. Usa il pulsante per scaricarlo.")
        except Exception as e:
            st.error(f"Errore lettura PDF generato: {e}")

# Download button + fallback
if st.session_state.get("pdf_bytes"):
    st.download_button(
        label="Scarica il PDF",
        data=st.session_state["pdf_bytes"],
        file_name=st.session_state["output_name"],
        mime="application/pdf",
        key="download-pdf"
    )
    b64 = base64.b64encode(st.session_state["pdf_bytes"]).decode()
    href = f'<a href="data:application/pdf;base64,{b64}" download="{st.session_state["output_name"]}">Scarica (fallback)</a>'
    st.markdown(href, unsafe_allow_html=True)
