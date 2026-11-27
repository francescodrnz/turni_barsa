# 0008 — Indicazioni della settimana nel PDF generato

Stato: decisa il 2026-11-27
Unità: trasversale

## Contesto
Chi riceve i turni vuole nel PDF anche le indicazioni scritte nei riquadri a
destra della tabella. Il testo si legge bene, ma cambia spesso: nelle sett.
44-49 è cambiato in due settimane su quattro. Non basta riportarlo per intero:
per ogni turno conviene dire quale indicazione lo riguarda, senza che
qualcuno debba aggiornare regole ogni settimana.

## Alternative
- A) Regole scritte nel codice o in un file del repo, una per indicazione:
  precise, ma vanno aggiornate ogni 1-2 settimane.
- B) Etichette scritte a mano nell'app: Streamlit Cloud non salva i file, si
  riscrivono ogni settimana.
- C) Tre livelli: testo intero sempre; collegamento ai turni del primo luogo che
  l'indicazione nomina ("Nota N"); se c'è la chiave, Gemini riassume in circa
  5 parole e restringe a orari e giorni, con il risultato controllato contro
  la tabella e il ripiego sul livello sotto.

## Scelta
C. Il collegamento va sul **primo** luogo nominato, il soggetto: con tutti i
luoghi nominati la nota del Borgia ("…aprire i giardini di viale Manzoni")
finiva anche su chi lavora al Manzoni. Gemini può solo restringere quel luogo
(orari, giorni) e riassumere; non aggiunge luoghi, perché le uniche note senza
luogo (asterischi, pezzi di legenda) non hanno un riferimento nella tabella.
Layout: variante B di tre prototipi (in fondo prima le indicazioni dei tuoi
turni, poi le altre in grigio; striscia dei giorni compatta accanto al nome);
la C (colonna a destra) tagliava i luoghi. Su richiesta dell'utente le
etichette vanno accanto al luogo quando ci stanno, sotto quando no.

## Conseguenze verificate
- 2026-11-27, sett. 49: 5 note, 2 di pulizia; Crudele ha la nota del Puttilli
  sui 3 turni al Puttilli e quella del Simeone al Chieffi, Venanzio quella del
  Borgia sui 4 Borgia. Sett. 02-08: Rizzi al Manzoni senza la nota del Borgia.
- Turni di tutte le 359 persone dei 22 PDF di `pdf_turni/` identici a prima.
- PDF: una pagina ed entro i margini su tutto `pdf_turni/`, con un'etichetta
  di 45 caratteri e sul caso pieno (Iodice 22-28 gen con note finte, prima al
  73%: ora le etichette vanno accanto al luogo e la pagina è piena).
- Gemini: chiave finta → 400, ripiego su "Nota N" col messaggio; risposta finta
  con un luogo in più, un orario non della tabella, un'etichetta troppo lunga,
  giorni vuoti e una voce non valida → tenuto solo quello che regge.
  App in locale senza `secrets.toml`: il PDF esce con "Nota N".
- Da tenere d'occhio: la prova con una chiave vera; i limiti del piano
  gratuito; note scritte con il soggetto dopo un altro luogo.
