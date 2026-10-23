# 0002 — Niente struttura di riserva nel codice: structure.json è l'unica fonte

Stato: superata da 0003 (decisa il 2026-10-23)
Unità: trasversale

## Contesto
`get_hardcoded_structure()` in `main.py` aveva una copia della struttura da
usare se `structure.json` mancava o non si leggeva. Non era più allineata al
file (layout vecchio, prima della sett. 44): se il JSON si fosse rotto, i turni
sarebbero usciti sbagliati senza nessun avviso.

## Alternative
- A) Allineare la copia a `structure.json`: l'app gira anche senza il file, ma
  le copie restano due e si disallineano di nuovo al prossimo cambio di righe.
- B) Togliere la copia e fermarsi con un errore se il file manca o è rotto:
  una sola fonte, nessun errore silenzioso. Su Streamlit Cloud il file viene
  dal repo, quindi c'è sempre.

## Scelta
B — un errore visibile è meglio di turni sbagliati in silenzio, ed è lo stesso
problema che aveva già fatto danni con la sett. 44.

## Conseguenze verificate
Con `structure.json` presente la struttura caricata è identica al file (62
indici). Con il file assente esce `FileNotFoundError`, e con un JSON non valido
`RuntimeError`, entrambi con il percorso nel messaggio. Non verificato in
Streamlit: l'errore lì compare come eccezione a schermo.
