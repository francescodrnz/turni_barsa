# 0007 — Layout del PDF generato: striscia della settimana più elenco dei giorni

Stato: decisa il 2026-11-20
Unità: trasversale

## Contesto
Il PDF generato è l'unica cosa che vede chi riceve i turni, letto sul telefono e
a volte stampato. Era una tabella fpdf 1.7 fatta a mano: senza la settimana nel
documento, una riga per turno col giorno ripetuto, assenze uguali ai turni, una
colonna "Pulizia bagni" quasi sempre vuota e testo piccolo su un A4 mezzo vuoto.

## Alternative
Tre prototipi, provati sulle sett. 47-48 e sulle settimane più piene di
`pdf_turni/` (Crudele 12-18 ago, Iodice 22-28 gen con 3 turni al giorno, Curci F.
10-16 nov con 4 pulizie):
- A) Tabella pulita (giorno | luogo | orario, solo linee orizzontali): sobria,
  stampa bene, ma i luoghi lunghi vanno tagliati in una colonna stretta.
- B) Una scheda per giorno con blocco data colorato: la più moderna nelle
  settimane leggere; in quelle piene orario e luogo su due righe la fanno
  rimpicciolire all'89% e i luoghi si leggono male.
- C) Striscia dei sette giorni in alto (lavoro / assenza a colpo d'occhio, con
  Notte/Mattina/Pomeriggio) ed elenco dei giorni sotto.

## Scelta
C: resta grande anche nella settimana più piena (scala 1,13 contro 0,89 di B) e
la striscia dice com'è fatta la settimana prima di leggere i dettagli. Ritocchi
chiesti: riquadri chiari per l'inchiostro, etichette della parte del giorno al
posto di "N turni", orari allineati.

Per farlo si passa da `fpdf` 1.7.2 (ferma, senza font TrueType né angoli
arrotondati) a `fpdf2`, col carattere Inter in `fonts/` (OFL) e `uharfbuzz` per
le cifre tabulari (`tnum`): con le cifre a larghezza fissa disegnate a mano l'"1"
lasciava un buco.

## Conseguenze verificate
- 2026-11-20: tutte le settimane di prova e un caso costruito (turno senza
  orario, orario scritto a mano, giorno mancante, permesso in un giorno di lavoro,
  turno di notte, "Riposo - <luogo> (chiuso)") stanno in una pagina, senza testo
  che esce o si sovrappone. 0,3 s e 26 KB per PDF.
- Regola Mattina/Pomeriggio provata sui 69 orari distinti di `pdf_turni/`: 31
  mattina, 35 pomeriggio, 3 tutti e due; i turni da mezzanotte sono "Notte".
- Da tenere d'occhio: Streamlit Cloud dopo il cambio di dipendenze; luoghi con
  nomi molto più lunghi di "Giardini viale Manzoni-Via Da Vinci".
