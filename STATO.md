# Stato del progetto

Aggiornato il 2026-11-27.

App Streamlit (deploy da `main`) e script locale che estraggono i turni di una
persona dal PDF settimanale "servizio custodia e pulizia" e generano un PDF
riassuntivo.

Il parser legge luogo e orario direttamente dal PDF, riconoscendo i blocchi dai
bordi che Excel disegna in colonna 0 (decisione 0003), compreso il caso del
bordo mancante fra orario e lunedì. Le scansioni senza testo vengono rifiutate
con un messaggio chiaro. La pulizia bagni del Castello viene dal colore delle
celle e dall'orario del turno (decisione 0006). Il nome del file generato viene
dai giorni della tabella e dalla data di creazione del PDF (decisione 0005).

Il PDF generato (decisioni 0007 e 0008) ha in alto il nome con la striscia
compatta dei sette giorni accanto, poi un blocco per giorno con orari, luoghi
ed etichette, e in fondo le indicazioni della settimana lette a destra della
tabella: prima quelle che riguardano i turni della persona, poi le altre in
grigio. Ogni indicazione va sui turni del primo luogo che nomina, con
un'etichetta colorata "Nota N"; con la chiave Gemini nei Secrets l'etichetta
diventa un riassunto di poche parole, ristretto a orari e giorni. Sempre una
pagina sola. Nell'app la tab Indicazioni mostra da dove vengono le etichette e
permette di cambiarle o toglierle per la sessione.

Verificato in locale su tutto `pdf_turni/`, sett. 49 compresa: turni identici a
prima per tutte le persone, PDF in una pagina ed entro i margini, CLI e app
senza chiave, Gemini con chiave finta e risposte finte. Non ancora provati:
Gemini con una chiave vera e il salvataggio dalla tab Indicazioni, entrambi in
TODO.md con la prova su Streamlit Cloud dopo il push.
