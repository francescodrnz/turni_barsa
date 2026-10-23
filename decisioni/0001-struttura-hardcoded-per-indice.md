# 0001 — Significato delle righe scritto a mano, per indice di riga

Stato: superata da 0003 (decisa il 2026-03-27)
Unità: trasversale

## Contesto
Il PDF settimanale non dice riga per riga luogo e orario: i luoghi sono
scritti una volta per blocco (spesso in una cella finta al centro), alcuni
orari coprono due righe, in colonna 0 ci sono qualificatori ("domenica",
"sabato e domenica") invece di luoghi.

## Alternative
- A) Leggere luogo e orario dal PDF: fragile per i motivi sopra.
- B) Mappa a mano indice di riga → (luogo, orario) in `structure.json`,
  correggibile da Streamlit (provvisoria) o esportabile e committata
  (permanente).
- C) Screenshot a un modello con visione via API: scartata per il costo.

## Scelta
B — la struttura generale cambia di rado e la correzione a mano è veloce.

## Conseguenze verificate
Quando l'azienda aggiunge una riga, tutto quello che sta sotto scala di uno
senza errori visibili (sett. 44: Malattia letta come Ferie). Alternativa
allo studio in `lavori/allineamento-righe-per-contenuto.md`.
