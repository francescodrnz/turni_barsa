# Turnizio Bar.S.A.

## A cosa serve
Dal PDF settimanale "servizio custodia e pulizia" di Bar.S.A. estrae i turni di
una persona (giorno, luogo, orario) e genera un PDF riassuntivo con solo quelli.
Due interfacce sullo stesso parser: l'app Streamlit (`app.py`, deploy da `main`
su Streamlit Cloud) e uno script interattivo da terminale (`main.py`).

## Com'è fatto

**Parser (`main.py`)** — decisione 0003
- `read_shift_table` apre il PDF con pdfplumber e prende, fra tutte le pagine,
  la tabella più lunga con l'header dei giorni (celle tipo "lunedì 26") fra le
  prime tre righe. I giorni vanno bene sia con l'accento sia con l'apostrofo
  (`normalize_day_name`). Internamente mercoledì si scrive `mercoledi'`.
- **Blocchi**: in colonna 0 Excel disegna un bordo orizzontale (rect sottile
  scuro) solo fra un blocco e l'altro. `_segments` divide le righe in blocchi
  con quei bordi. `_text_in` legge il testo di un blocco intero, prendendo i
  caratteri con il centro dentro il riquadro: così funzionano sia le celle
  unite vere sia quelle finte (testo nella cella centrale).
- **Luogo** = etichetta del blocco. Se l'etichetta contiene solo parole sui
  giorni (`is_qualifier`: "domenica", "sabato, domenica e fest. Feriali", "dal
  Lun. al Sabato"…), il blocco eredita il luogo del blocco sopra. Un blocco
  vuoto e senza orari (riga di separazione) azzera il luogo. Le righe header
  (col. 1 = "turno") non producono turni.
- **Orario** = la cella della colonna 1, segmentata con lo stesso criterio:
  un orario su due righe vale per entrambe. `normalize_time` lo riporta a
  `HH:MM-HH:MM` (`12,00-18,00`, `09:0011:00`, `15::00`, nome attaccato). Un
  orario scritto nella cella del dipendente ha la precedenza.
- **Controlli**: PDF che non si apre, scansione senza testo, nessun header dei
  giorni, meno di `MIN_LOCATIONS` (5) luoghi distinti → `ValueError` con un
  messaggio. Non si estraggono turni da una tabella che non ha la forma attesa.
- `extract_shifts_for_person(table, cognome)` ritorna `(turni, avvisi)`. Ogni
  cella di una colonna giorno che contiene il cognome (sottostringa, senza
  distinzione di maiuscole) diventa un turno. Avvisi: cognome in una riga
  senza luogo ("Luogo non riconosciuto"), riga di un luogo di lavoro senza
  orario, cognome assente dal PDF.
- Luoghi con "chiuso/chiusa" diventano "Riposo - <luogo>". Gli stati
  (`STATUS_LOCATIONS`: Riposo, Ferie, Malattia, Assente, Permessi, Infortunio,
  Non lavora) non hanno orario. I giorni dove il cognome non compare diventano
  "Riposo".
- **Pulizia bagni** (decisione 0004): `_legend` legge la legenda a destra
  della tabella. Ogni barretta colorata vuota prende il significato dal
  paragrafo subito sopra ("19:00"/"ripasso" → `19:00`, "mattino"/"12:00" →
  `Mattina`); i rettangoli con testo dentro sono evidenziazioni e si saltano.
  `read_shift_table` salva il colore di ogni cella dei giorni (`colori`, con
  `_fill_at`) e la legenda (`legenda`). A Giardini del Castello,
  `extract_shifts_for_person` mette nel quinto campo il significato del
  colore (`_legend_meaning`, tollera sfumature fino a 0,1), "No" per una cella
  bianca, un avviso per un colore che non è in legenda. Senza legenda il campo
  resta vuoto.
- Le celle unite allargano verso destra e verso il basso i bbox di righe e
  colonne di pdfplumber: per trovare una cella si usano solo i bordi sinistro
  e superiore (`col.bbox[0]`, `row.bbox[1]`).
- `write_shifts_to_pdf` genera il PDF con fpdf. Se fra i turni c'è Giardini del
  Castello, aggiunge la colonna "Pulizia bagni" ("No" dove il valore manca). Il
  nome del file è `Turni <cognome> dal … .pdf`, preso dal nome del PDF di
  partenza.

**App (`app.py`)**
- Barra laterale: si carica il PDF da file o da link Adobe Acrobat. Il link
  viene risolto da `download_adobe_pdf`, che legge il JSON `dc_data` della
  pagina e recupera anche il nome originale del file. Poi si sceglie il cognome
  (default "Crudele Francesco") e si preme Genera turni. Il PDF viene scritto
  in un file temporaneo solo per la lettura, poi cancellato. Gli errori di
  lettura compaiono come `st.error`.
- Tab *PDF generato*: gli avvisi dell'estrazione in cima, poi anteprima e
  download.
- Tab *Modifica turni*: correzioni **provvisorie**, solo per questa
  elaborazione. Si fanno nella tabella modificabile con "Salva modifiche e
  rigenera PDF", oppure con il form "Aggiungi un nuovo turno". Vivono nella
  sessione e si perdono ricaricando la pagina.
- Tab *Lettura PDF*: per ogni riga del PDF, etichetta del blocco, luogo e
  orario assegnati e nomi (`table_debug_rows`). Serve a capire se un turno
  sbagliato viene da una lettura sbagliata.

`old/` contiene script vecchi non più usati.

## Come si usa
- **App online**: si apre l'app su Streamlit Cloud, si carica il PDF (o si
  incolla il link Adobe), si scrive il cognome e si scarica il PDF. Se compare
  un avviso, si controlla la riga nella tab Lettura PDF e si corregge il turno
  nella tab Modifica turni.
- **In locale**: il `.venv` del repo è creato con `uv` e non ha `pip`; i
  pacchetti si installano con `uv pip install -p .venv/bin/python -r
  requirements.txt`. Per il solo parser bastano `pdfplumber` e `fpdf`. Si lancia `main.py` da una cartella che contiene il PDF: il
  programma propone i file che iniziano con "servizio custodia", chiede il
  cognome, stampa avvisi e turni e scrive il PDF nella cartella corrente.
- **In locale, app**: oltre ai requisiti serve `poppler-utils` di sistema
  (`packages.txt`, serve a `pdf2image`), poi `.venv/bin/streamlit run app.py`.

Dopo una modifica al parser si rigenerano i turni di Crudele Francesco
sull'ultimo PDF, si confrontano a occhio con la tabella originale e si lancia
il controllo su tutti i PDF di `pdf_turni/` (Comandi utili).

## Misure
- 2026-10-23, sett. 44 (26/10–01/11/2026): turni identici al vecchio metodo
  per indice per tutte le 25 persone (233 turni), nessun avviso. I turni di
  Crudele sono stati confrontati con la tabella originale.
- 2026-10-23, `pdf_turni/`: 18 PDF con testo letti senza errori, 535 persone e
  4693 turni, nessuna riga col cognome senza luogo o senza orario. 5 scansioni
  rifiutate con il messaggio sulla scansione.
- 2026-10-23, pulizia bagni su `pdf_turni/`: sett. 44 6 "19:00" e 7
  "Mattina"; 11 PDF con la sola regola delle 19:00, 7 "19:00" ciascuno;
  gennaio e febbraio 7 + 7; nessun valore sui PDF senza legenda. Un solo
  avviso (29 dic, giovedì 01).

## Limiti e comportamenti noti
- **Dipende dai bordi di Excel**: se l'azienda cambia lo stile dei bordi in
  colonna 0, i blocchi non si riconoscono più. Con meno di 5 luoghi l'estrazione
  si ferma con un errore. Con un cambio parziale potrebbe passare: in caso di
  dubbio, guardare la tab Lettura PDF.
- **Scansioni** (PDF fatti con la fotocopiatrice, solo immagini): non si
  leggono, errore "Il PDF è una scansione senza testo".
- **Qualificatori nuovi**: un'etichetta di colonna 0 che dice quando vale il
  blocco sopra, ma con parole diverse dai giorni, da dal/al/e, da
  festivi/feriali/solo, verrebbe presa per un luogo. Rimedio: aggiungere la
  parola a `QUALIFIER_WORDS` in `main.py`.
- **Stati nuovi** (es. "Congedo"): finiscono come luogo con l'avviso "orario
  non trovato". Rimedio: aggiungerli a `STATUS_LOCATIONS`.
- **Pulizia bagni**: dipende dalla legenda. Una regola scritta con parole
  nuove (senza "19:00", "ripasso", "mattino", "12:00") non viene riconosciuta e
  le celle di quel colore danno l'avviso "colore che non è in legenda".
  Rimedio: aggiungere la parola alle chiavi in `_legend`. Una barretta con
  sfumatura molto diversa dalle celle (29 dic, viola) dà lo stesso avviso: si
  corregge a mano nella tab Modifica turni.
- I nomi dei luoghi sono quelli scritti nel PDF, maiuscole comprese ("Permessi
  vari").
- Il cognome si cerca come sottostringa: "Rossi" trova anche "Rossini".
  Conviene scrivere cognome e nome. La CLI chiede almeno 3 caratteri.
- CLI: non permette di correggere i turni, solo di estrarli e generare il PDF.
  Le correzioni si fanno dall'app.
- Tab Modifica turni: le celle lasciate vuote in una riga aggiunta finiscono
  nel PDF come testo vuoto, le righe del tutto vuote si scartano al salvataggio.
- I PDF dei turni (originali e generati) contengono nomi, malattie e permessi
  dei colleghi: non vanno messi nel repo. `.gitignore` esclude `*.pdf`; per le
  prove in locale si tengono in `pdf_turni/`.

## Comandi utili
```bash
# CLI interattiva (scrive il PDF nella cartella corrente)
.venv/bin/python main.py

# Turni di Crudele senza domande (debug no, nome file, cognome, Invio finale).
# Da una cartella che contiene solo quel PDF: se ci sono file "servizio
# custodia…" la CLI chiede prima quale scegliere.
printf 'n\n<file>.pdf\nCrudele\n\n' | /percorso/repo/.venv/bin/python /percorso/repo/main.py

# Righe del PDF con luogo e orario assegnati
.venv/bin/python -c "import main, sys; [print(r) for r in main.table_debug_rows(main.read_shift_table(sys.argv[1]))]" "file.pdf"

# Controllo su tutti i PDF di pdf_turni/: atteso "ok" ovunque, ERRORE solo sulle scansioni
.venv/bin/python -c "
import main, glob
for p in sorted(glob.glob('pdf_turni/*.pdf')):
    try: t = main.read_shift_table(p)
    except ValueError as e: print('ERRORE', p, e); continue
    bad = [r['riga'] for r in t['rows'] if not r['header'] and any(r['celle'][c] for c in t['days'])
           and (not r['luogo'] or not (r['orario'] or main.is_status_location(r['luogo'])))]
    print('ok' if not bad else 'DA GUARDARE', p, bad)"

# Legenda e celle colorate di Giardini del Castello (colore → significato)
.venv/bin/python -c "
import main, sys
t = main.read_shift_table(sys.argv[1]); print(t['legenda'])
for r in t['rows']:
    if r['luogo'] and 'castello' in r['luogo'].lower():
        print(r['orario'], {t['days'][c][0]: (r['celle'][c], r['colori'][c]) for c in t['days'] if r['colori'][c]})" "file.pdf"

# App in locale
uv pip install -p .venv/bin/python -r requirements.txt && .venv/bin/streamlit run app.py
```

## Decisioni collegate
- [0004](decisioni/0004-pulizia-bagni-dalla-legenda.md) — Pulizia bagni dal
  colore delle celle, con il significato letto dalla legenda.
- [0003](decisioni/0003-luoghi-dai-bordi-del-pdf.md) — Luogo e orario letti dai
  bordi del PDF, senza `structure.json`.
- [0001](decisioni/0001-struttura-hardcoded-per-indice.md) e
  [0002](decisioni/0002-niente-struttura-di-riserva.md) — mappa per indice in
  `structure.json`, superate dalla 0003.
