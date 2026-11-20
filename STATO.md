# Stato del progetto

Aggiornato il 2026-11-20.

App Streamlit (deploy da `main`) e script locale che estraggono i turni di una
persona dal PDF settimanale "servizio custodia e pulizia" e generano un PDF
riassuntivo.

Il parser legge luogo e orario direttamente dal PDF, riconoscendo i blocchi dai
bordi che Excel disegna in colonna 0 (decisione 0003). Le scansioni senza testo
vengono rifiutate con un messaggio chiaro. Nell'app, la tab "Lettura PDF" mostra
riga per riga cosa è stato letto; gli avvisi compaiono in cima al PDF generato.

La colonna "Pulizia bagni" di Giardini del Castello si riempie da sola ("19:00",
"Mattina", "No") dal colore delle celle: la legenda accanto alla tabella dice
quali colori contano, il valore viene dall'orario del turno (decisione 0006,
che supera la 0004). Verificato su tutti i PDF di `pdf_turni/`, comprese la
sett. 47 e la "dal 02 al 08", dove la legenda ha una disposizione diversa.

Quando in una riga manca il bordo fra la colonna dell'orario e il lunedì, i
nomi del lunedì vengono riletti per posizione (prima finivano persi, e quel
giorno risultava "Riposo"). Verificato sulla sett. 48 e su tutto `pdf_turni/`.

Il nome del PDF generato non dipende più dal nome del file in input: viene dai
giorni della tabella e dalla data di creazione del PDF (decisione 0005).
Verificato su `pdf_turni/`, con la sett. 46 da link Adobe e con lo script.

Il PDF generato ha un layout nuovo (decisione 0007): periodo nell'intestazione,
striscia dei sette giorni con Mattina/Pomeriggio, un blocco per giorno, assenze
in grigio, pulizia bagni come etichetta sotto il luogo, sempre in una pagina.
Passa a fpdf2 con il carattere Inter in `fonts/` e `uharfbuzz`. Verificato in
locale (script, CLI, app); su Streamlit Cloud va provato dopo il push, con un
"Reboot app" se l'import di `week_period` o le dipendenze nuove danno errore.

Provati a mano su Streamlit Cloud: caricamento da file, nome del file scaricato
(anche a cavallo di due mesi), pulizia bagni dall'orario (sett. 47) e il lunedì
di Crudele nella sett. 48 (prima del nuovo layout). Aperto in TODO.md: il push
e la prova del nuovo PDF su Streamlit Cloud.
