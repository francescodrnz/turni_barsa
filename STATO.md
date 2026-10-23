# Stato del progetto

Aggiornato il 2026-10-23.

App Streamlit (deploy da `main`) e script locale che estraggono i turni di una
persona dal PDF settimanale "servizio custodia e pulizia" e generano un PDF
riassuntivo. Il significato di ogni riga della tabella è scritto a mano in
`structure.json`, indicizzato per posizione della riga. È l'unica fonte: nel
codice non c'è più una struttura di riserva.

`structure.json` è allineata al layout della sett. 44 (26/10–01/11/2026),
orari compresi. Il parser accetta i giorni sia con l'accento sia con
l'apostrofo. Nella tab Modifica turni si possono aggiungere righe con celle
vuote senza che la rigenerazione del PDF vada in errore. Il `.venv` locale
(creato con `uv`) ha tutti i requisiti installati.

Prossimo passo: le verifiche in TODO.md (prova su Streamlit Cloud della tab
Modifica turni, turni sulla sett. 44, app in locale), poi il bug della CLI.
