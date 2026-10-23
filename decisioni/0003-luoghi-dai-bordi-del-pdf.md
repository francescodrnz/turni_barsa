# 0003 — Luogo e orario letti dai bordi del PDF, senza structure.json

Stato: decisa il 2026-10-23
Unità: trasversale
Supera: 0001, 0002

## Contesto
Con la mappa per indice di riga (0001), ogni riga aggiunta o tolta dall'azienda
fa scalare in silenzio tutto quello che sta sotto (sett. 44: Malattia letta
come Ferie). Inoltre gli orari vanno aggiornati a mano a ogni cambio di stagione.
La 0001 aveva scartato la lettura dal PDF perché le celle finte (luogo scritto
solo nella cella centrale di un blocco senza bordi) sembravano illeggibili.

## Alternative
- A) Tenere la mappa per indice: semplice, ma si rompe in silenzio a ogni
  cambio di righe e va mantenuta a mano.
- B) Allineare le righe del PDF alla mappa per contenuto, con un algoritmo
  tipo diff: tiene `structure.json`, ed è fragile proprio quando cambiano tanti
  orari e righe nella stessa settimana.
- C) Leggere i blocchi dai bordi. In colonna 0 Excel disegna un bordo
  orizzontale solo fra un blocco e l'altro, mai dentro un blocco: il luogo è
  l'etichetta del blocco, un'etichetta che contiene solo giorni ("domenica",
  "dal Lun. al Sabato") eredita il luogo del blocco sopra, e l'orario si legge
  dalla cella della colonna 1, segmentata con lo stesso criterio.

## Scelta
C — non serve nessuna mappa scritta a mano, legge anche luoghi e orari mai
visti prima, e quando la forma del PDF cambia si ferma con un errore invece di
sbagliare in silenzio.

## Conseguenze verificate
- Sett. 44: turni identici al metodo A per tutte le 25 persone (233 turni).
  Unica differenza: "Permessi vari" con la grafia del PDF.
- 17 PDF storici con layout diversi (blocchi di 4 righe invece di 5, luoghi
  aggiunti o tolti, Pala Marchisella, Infortunio, Non lavora): 535 persone e
  4693 turni, nessuna riga col cognome senza luogo o senza orario. Nei
  confronti con le vecchie versioni di `structure.json`, quando i due metodi
  davano risultati diversi era la struttura a essere sbagliata.
- Le 5 scansioni (Konica Minolta, solo immagini) non si leggono con nessun
  metodo: ora danno un errore esplicito.
- Bordi spariti, simulati: errore "Struttura del PDF non riconosciuta".
- Resta da tenere d'occhio: se Excel cambia lo stile dei bordi ma lascia
  almeno 5 luoghi riconoscibili, il controllo di forma non scatta. Allora la
  tab "Lettura PDF" è il posto dove accorgersene.
