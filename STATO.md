# Stato del progetto

Aggiornato il 2026-10-23.

App Streamlit (deploy da `main`) e script locale che estraggono i turni di una
persona dal PDF settimanale "servizio custodia e pulizia" e generano un PDF
riassuntivo. Il significato di ogni riga della tabella è scritto a mano in
`structure.json`, indicizzato per posizione della riga.

`structure.json` è allineata al layout della sett. 44 (26/10–01/11/2026),
orari compresi. Il parser accetta i giorni sia con l'accento sia con
l'apostrofo.

Prossimo passo: scrivere `README.md` (vedi TODO.md).
