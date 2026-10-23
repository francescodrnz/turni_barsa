# 0004 — Pulizia bagni dal colore delle celle, con il significato letto dalla legenda

Stato: decisa il 2026-10-23
Unità: trasversale

## Contesto
A Giardini del Castello chi fa i turni colora le celle di chi pulisce i bagni:
un colore per il ripasso delle 19:00, uno per la pulizia del mattino. Accanto
alla tabella c'è la legenda, cioè una barretta colorata sotto il testo della
regola. Fino a oggi la colonna "Pulizia bagni" del PDF generato era sempre
"No", e il "Sì" si metteva a mano. Il PDF viene da Excel, quindi i colori sono
nel file come il testo: non serve OCR.

## Alternative
- A) Fissare i colori nel codice (celeste = 19:00, beige = mattino): è
  semplice, ma i colori cambiano di settimana in settimana (pesca, rosa,
  verde, azzurro, celeste) e si tornerebbe a una struttura scritta a mano,
  come quella tolta con la 0003.
- B) Leggere la legenda: ogni barretta vuota a destra della tabella prende il
  significato dal paragrafo subito sopra ("19:00"/"ripasso" → "19:00";
  "mattino"/"12:00" → "Mattina"). Il colore delle celle di Giardini del
  Castello si confronta con quello delle barrette.

## Scelta
B. Regge i cambi di colore e le regole che compaiono o spariscono. Senza
legenda non indovina: la colonna resta "No" come prima. Una cella colorata con
un colore che non è in legenda dà un avviso, senza mettere un valore.

## Conseguenze verificate
- Sett. 44: 6 "19:00" (giovedì la cella è bianca) e 7 "Mattina", uguali a
  quello che si vede nella tabella.
- 11 PDF storici con la sola regola delle 19:00: 7 "19:00" ciascuno, nessun
  "Mattina". Gennaio e febbraio ("1° passaggio ore 12:00 / 2° passaggio ore
  19:00"): 7 + 7. I PDF senza legenda restano senza valori.
- Excel a volte usa per la cella una sfumatura diversa da quella della
  barretta (gennaio: scarto 0,05). Si accetta uno scarto fino a 0,1 sul canale
  peggiore. Il viola del 29 dic (scarto 0,22, passaggio straordinario del
  01/01) resta un avviso: è l'unico su tutti i PDF.
- I rettangoli colorati con del testo dentro sono evidenziazioni, non
  barrette. Lo stesso pesca colora anche righe di altri luoghi: per questo il
  colore conta solo a Giardini del Castello.
