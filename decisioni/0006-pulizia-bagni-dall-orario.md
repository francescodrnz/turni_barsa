# 0006 — Pulizia bagni: la legenda dice quali colori, l'orario del turno dice quale pulizia

Stato: decisa il 2026-11-13
Unità: trasversale
Supera: 0004

## Contesto
Con la 0004 ogni barretta della legenda prendeva il significato dal paragrafo
subito sopra. Nella sett. 47 le barrette stanno sopra il testo della regola:
il marroncino del mattino è stato letto come "19:00", l'azzurro delle 14-21 si è
perso. Nella "dal 02 al 08" il marroncino sta sopra il testo delle 19:00, lontano
da quello del mattino. La posizione delle barrette rispetto al testo cambia di
settimana in settimana.

## Alternative
- A) Colori fissi nel codice (marroncino = Mattina, azzurro = 19:00): la modifica
  più piccola, ma nei PDF storici i colori sono cambiati 6-7 volte; al prossimo
  cambio la colonna tornerebbe "No" o piena di avvisi.
- B) La legenda dice solo quali colori indicano la pulizia (barretta vuota sopra
  o sotto un testo di regola); il significato viene dall'orario del turno della
  cella: "19:00" se il turno comprende le 19:00, "Mattina" se comincia prima di
  mezzogiorno.
- C) Barretta abbinata al paragrafo più vicino, sopra o sotto: sistema la 47 ma
  sbaglia la 02-08, dove tutte e due le barrette finiscono su "19:00".

## Scelta
B. In tutti i PDF di `pdf_turni/` il colore del mattino sta sui turni 08-14 e
quello delle 19:00 sui turni 14-21 o 16-23: l'orario dice già quale pulizia è, e
regge sia i cambi di colore sia quelli di impaginazione della legenda.

## Conseguenze verificate
- Sett. 47: 4 "Mattina" e 7 "19:00" (prima 4 "19:00" sbagliati e 7 celle senza
  valore); restano gli avvisi per il verde, che non è in legenda.
- Dal 02 al 08: 7 "Mattina" e 7 "19:00" (prima 7 celle senza valore, con
  avviso).
- Tutti gli altri PDF di `pdf_turni/`: valori e avvisi identici a prima,
  compreso il viola del 29 dic.
- Da tenere d'occhio: un colore di legenda su un turno che non comprende le 19 e
  comincia dopo mezzogiorno dà l'avviso "né di mattina né delle 19:00". Un
  turno lungo che comprende sia la mattina sia le 19 vale "19:00".
