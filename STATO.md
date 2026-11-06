# Stato del progetto

Aggiornato il 2026-11-06.

App Streamlit (deploy da `main`) e script locale che estraggono i turni di una
persona dal PDF settimanale "servizio custodia e pulizia" e generano un PDF
riassuntivo.

Il parser legge luogo e orario direttamente dal PDF, riconoscendo i blocchi dai
bordi che Excel disegna in colonna 0 (decisione 0003). Le scansioni senza testo
vengono rifiutate con un messaggio chiaro. Nell'app, la tab "Lettura PDF" mostra
riga per riga cosa è stato letto; gli avvisi compaiono in cima al PDF generato.

La colonna "Pulizia bagni" di Giardini del Castello si riempie da sola ("19:00",
"Mattina", "No") dal colore delle celle, con il significato letto dalla legenda
accanto alla tabella (decisione 0004).

Il nome del PDF generato non dipende più dal nome del file in input: viene dai
giorni della tabella e dalla data di creazione del PDF (decisione 0005).
Verificato su `pdf_turni/`, con la sett. 46 da link Adobe e con lo script.

Provati a mano su Streamlit Cloud: caricamento da file, nome del file scaricato
(anche a cavallo di due mesi) e colonna Pulizia bagni.

Nessun lavoro aperto in TODO.md.
