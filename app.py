import streamlit as st
from main import parse_pdf, write_shifts_to_pdf
import tempfile, os

st.title("Generatore Turni in PDF")

uploaded_file = st.file_uploader("Carica il PDF dei turni", type="pdf")
surname = st.text_input("Cognome")

if uploaded_file and surname:
    if st.button("Genera PDF"):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded_file.read())
            tmp_path = tmp.name

        shifts = parse_pdf(tmp_path)
        write_shifts_to_pdf(shifts, tmp_path, surname)
        
        output_name = f"Turni {surname}.pdf"
        st.download_button(
            label="Scarica il PDF",
            data=open(output_name, "rb").read(),
            file_name=output_name,
            mime="application/pdf"
        )
        os.remove(tmp_path)
