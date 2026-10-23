# Stato del progetto

Aggiornato il 2026-10-23.

App Streamlit (deploy da `main`) e script locale che estraggono i turni di una
persona dal PDF settimanale "servizio custodia e pulizia" e generano un PDF
riassuntivo.

Il parser legge luogo e orario direttamente dal PDF, riconoscendo i blocchi dai
bordi che Excel disegna in colonna 0 (decisione 0003). Verificato su sett. 44 e
su 17 PDF storici con layout diversi, senza errori né avvisi. Le scansioni
senza testo vengono rifiutate con un messaggio chiaro. Nell'app, la tab "Lettura
PDF" mostra riga per riga cosa è stato letto; gli avvisi compaiono in cima al
PDF generato.

La colonna "Pulizia bagni" di Giardini del Castello si riempie da sola ("19:00",
"Mattina", "No") dal colore delle celle, con il significato letto dalla legenda
accanto alla tabella (decisione 0004). Verificata su tutti i PDF con testo e
provata nell'app in locale con la sett. 44. Non ancora provata su Streamlit
Cloud.

Nessun lavoro aperto in TODO.md.
