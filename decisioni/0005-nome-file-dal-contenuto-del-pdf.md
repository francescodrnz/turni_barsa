# 0005 — Nome del PDF generato dai giorni della tabella e dalla data di creazione

Stato: decisa il 2026-11-06
Unità: trasversale

## Contesto
Il nome del PDF generato veniva dalla regex `DAL.*\.pdf` sul nome del file in
input. Quel nome ora cambia ogni settimana ("44 sett. dipendenti.pdf", "sett. dal
02 al 08.pdf dipendenti.pdf", "sett. 46 dipendenti.pdf"), e il risultato era
`Turni X dal 02 al 08.pdf dipendenti.pdf` oppure `Turni X.pdf`.

## Alternative
- A) Regex più larghe sul nome del file: si inseguono le varianti, e "sett. 46"
  non contiene date.
- B) Titolo nei metadati del PDF: è il nome dell'Excel, scritto a mano. Spesso è
  "tabella custodia 2025.xlsx" o vuoto, e nella sett. 46 dice "sett 45".
- C) Titolo stampato nella pagina ("SETTIMANA DAL … AL …"): scoperto dopo la
  scelta. È scritto a mano e nella settimana del 2 novembre dice "02/10/2026".
- D) Giorni dell'intestazione della tabella più data di creazione del PDF: il
  lunedì con quel numero più vicino alla creazione dà mese e anno.

## Scelta
D. L'intestazione serve già al parser, che senza non legge il PDF, e il calendario
controlla che i giorni siano coerenti. Se la data non si trova, o i giorni non
seguono il calendario, il nome tiene i soli numeri: incompleto, ma mai sbagliato.

## Conseguenze verificate
- 17 PDF su 17 con il periodo nel nome coincidono, compresi i cambi di mese e di
  anno. Sett. 44, 45 e 46 (da link Adobe, metadati conservati) danno la settimana
  giusta.
- Date con lo stesso numero e lo stesso giorno della settimana distano almeno 28
  giorni: entro ±14 giorni la scelta è univoca. I PDF sono creati 3-5 giorni
  prima del lunedì.
- Da tenere d'occhio: un PDF rigenerato molto dopo la sua settimana, o senza
  metadati ed elaborato tardi, avrebbe il nome senza mese.
