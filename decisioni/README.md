# Decisioni

Una decisione per file, numerata e immutabile. Se una decisione viene superata,
non si riscrive: se ne apre una nuova e questa passa a "superata da NNNN".

Modello in `0000-modello.md`. Le regole stanno in `../CONVENZIONI.md`.

| N | Titolo | Stato | Unità |
|---|---|---|---|
| 0001 | Significato delle righe scritto a mano, per indice di riga | superata da 0003 | trasversale |
| 0002 | Niente struttura di riserva nel codice: structure.json è l'unica fonte | superata da 0003 | trasversale |
| 0003 | Luogo e orario letti dai bordi del PDF, senza structure.json | decisa | trasversale |
| 0004 | Pulizia bagni dal colore delle celle, con il significato letto dalla legenda | superata da 0006 | trasversale |
| 0005 | Nome del PDF generato dai giorni della tabella e dalla data di creazione | decisa | trasversale |
| 0006 | Pulizia bagni: la legenda dice quali colori, l'orario del turno dice quale pulizia | decisa | trasversale |
