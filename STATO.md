# Stato del progetto

Aggiornato il 2026-10-23.

App Streamlit (deploy da `main`) e script locale che estraggono i turni di una
persona dal PDF settimanale "servizio custodia e pulizia" e generano un PDF
riassuntivo.

Il parser legge luogo e orario direttamente dal PDF, riconoscendo i blocchi dai
bordi che Excel disegna in colonna 0 (decisione 0003). `structure.json` non
esiste più. Verificato su sett. 44 (identico al vecchio metodo per tutte le 25
persone) e su 17 PDF storici con layout diversi, senza errori né avvisi. Le
scansioni senza testo vengono rifiutate con un messaggio chiaro. Nell'app, la
tab Configurazione è diventata "Lettura PDF" (vista di controllo riga per
riga). Gli avvisi compaiono in cima al PDF generato. Provato in locale con
upload dal browser, non ancora su Streamlit Cloud.

Prossimo passo: push su `main` e prova del nuovo parser su Streamlit Cloud.
