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
- **Bordo mancante fra orario e lunedì**: senza quel bordo pdfplumber unisce
  la cella dell'orario con quelle dei giorni e il nome finisce in colonna 1.
  Quando la cella della colonna 1 si allarga oltre il suo bordo destro, le
  colonne dei giorni che copre si rileggono per posizione con `_text_in`.
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
- **Pulizia bagni** (decisione 0006): `_legend` legge la legenda a destra
  della tabella e ritorna la lista dei colori di pulizia: ogni barretta
  colorata vuota con subito sopra o sotto (`_paragraph_next_to`) un paragrafo
  con una parola di `LEGEND_KEYS` ("19:00", "ripasso", "mattino", "12:00"). I
  rettangoli con testo dentro sono evidenziazioni e si saltano.
  `read_shift_table` salva il colore di ogni cella dei giorni (`colori`, con
  `_fill_at`) e la legenda (`legenda`). A Giardini del Castello,
  `extract_shifts_for_person` mette nel quinto campo: "No" per una cella
  bianca; per un colore di legenda (`_is_legend_color`, tollera sfumature fino
  a 0,1) il valore dato dall'orario del turno (`_cleaning_from_time`: `19:00`
  se il turno comprende le 19:00, altrimenti `Mattina` se comincia prima di
  mezzogiorno); un avviso per un colore che non è in legenda o per un turno
  né di mattina né delle 19. Senza legenda il campo resta vuoto.
- Le celle unite allargano verso destra e verso il basso i bbox di righe e
  colonne di pdfplumber: per trovare una cella si usano solo i bordi sinistro
  e superiore (`col.bbox[0]`, `row.bbox[1]`).
- **Indicazioni della settimana** (decisione 0008): `_notes` legge i
  paragrafi di testo a destra della tabella, uno per riquadro (righe con lo
  stesso top ±3 pt, paragrafi a meno di 8 pt; scarta quelli con meno di 2
  parole, cioè il numero di pagina; una riga che finisce con "-" si unisce
  senza spazio). Finiscono in `table["indicazioni"]` con `n`, `testo`,
  `pulizia` (il testo senza spazi contiene "castello" e "bagn"/"wc"/"puliz":
  è la legenda della pulizia, resa già dall'etichetta ambra) e `asterisco`
  (comincia con "*": note dei PDF vecchi che rimandano a segni che nella
  tabella non ci sono). Tre livelli:
  - il testo intero va sempre nel PDF;
  - `link_notes`: una nota che non è di pulizia né ad asterisco va sul
    **primo** luogo della tabella che nomina (il soggetto, "l'addetto al
    borgia…"), confrontando le parole del nome del luogo (`_location_words`:
    almeno 4 lettere, senza `GENERIC_WORDS`) con il testo, entrambi passati per
    `_plain` (minuscole, senza accenti). Etichetta "Nota N". I luoghi citati
    dopo ("…aprire i giardini di viale Manzoni") non contano. Se il testo
    scrive un orario ("turno 10,00-12,00") o una parte del giorno
    ("pomeridiano", "antimeridiana", "mattino"), `_times_named_in` tiene solo
    gli orari del luogo che li toccano (la nota del Puttilli va solo sui turni
    di mattina; quella del Borgia, che nomina sia il pomeriggio sia 08-14,
    resta su tutti);
  - `notes_with_labels`: se c'è una chiave, `llm_notes` chiama Groq o Gemini
    (REST, `requests` importato solo lì) con le note e le righe della tabella
    come luogo, orario e giorni in cui la cella sembra un nome
    (`_looks_like_name`), **mai i nomi**. Gemini risponde con un'etichetta per
    nota e una per ogni turno (luogo + orario), così una nota che chiede cose
    diverse a turni diversi (Borgia: pomeriggio "Apri/chiudi Manzoni e Green
    Park", domenica 08-14 "Apertura antimeridiana") ha etichette diverse.
    `apply_llm` abbina per `n`, prende le etichette (max 45 caratteri) e
    restringe le regole dentro il luogo e gli orari del livello 2: orario
    uguale, altrimenti quelli che si sovrappongono in senso stretto; giorni con
    `normalize_day_name`; liste vuote = nessuna restrizione. Gemini non
    aggiunge luoghi e non allarga gli orari. Dopo le regole di Gemini restano
    quelle lette dal testo (`ripiego`): un turno che Gemini salta tiene la nota,
    con l'etichetta generale della nota. Qualunque errore (rete, codice
    non 200, risposta illeggibile) lascia il livello 2 e un messaggio.
  - `notes_for_shift` dice quali note valgono per un turno (luogo con
    `_plain`, orario con `normalize_time`, giorno con `normalize_day_name`):
    si calcola al momento del PDF, quindi segue le correzioni di Modifica turni.
- **PDF generato** (decisioni 0007 e 0008): `write_shifts_to_pdf(turni,
  percorso, cognome, periodo, indicazioni)` scrive una pagina A4 con fpdf2 e il
  carattere Inter di `fonts/` e ritorna `(percorso, avviso)`. In alto "Turni di
  lavoro", il nome e il periodo (`week_period`: "dal 12 al 18 agosto 2026",
  stessa fonte di `output_filename`; mese e anno del primo giorno solo se
  cambiano); accanto, a destra, la striscia compatta dei sette giorni:
  riquadro chiaro con Notte/Matt./Pom. (`parts_of_day`: Notte se il
  turno comincia prima delle 5, Mattina se prima delle 12, Pomeriggio se
  finisce dopo le 16 o comincia da mezzogiorno) oppure bianco col nome
  dell'assenza; un giorno senza righe ha il riquadro vuoto. Poi l'elenco: un
  blocco per giorno (`_days_for_pdf`), turni ordinati per inizio e fine, orari
  con le cifre tabulari di Inter (`tnum`, richiede `uharfbuzz`) così stanno in
  colonna; un giorno fatto solo di stati (`is_status_location`) è un'assenza in
  grigio, uno stato in un giorno di lavoro è una riga in corsivo. La pulizia
  bagni è un'etichetta ambra ("alle 19:00", "di mattina"; niente per "No" o
  vuoto, il testo così com'è per un valore scritto a mano); ogni indicazione
  attiva del turno è un'etichetta col suo colore (`NOTE_COLORS`) e il suo
  numero. Le etichette vanno accanto al luogo se ci stanno tutte sulla stessa
  riga, altrimenti sotto, una per riga, rimpicciolite fino al 75% e poi
  accorciate con "…". In fondo le indicazioni per intero (`readable_note`
  riporta in minuscolo i testi tutti maiuscoli): prima "per i tuoi turni"
  (collegate ai turni della persona, più quelle di pulizia se ha una pulizia),
  poi "altre" più piccole e in grigio. Le indicazioni hanno dimensione fissa;
  il corpo prende l'altezza che resta, con la scala più grande fra 0,6 e 1,45
  trovata per bisezione su una pagina di prova (dove vanno le etichette dipende
  dalla scala). Se non basta, le "altre" scendono fino a 6,5 pt; se non basta
  ancora, l'avviso.
- `output_filename` dà il nome del file, `Turni <cognome> dal 09 al 15
  novembre.pdf`, senza guardare il nome del PDF di partenza. Giorni e numeri
  vengono dall'intestazione della tabella; mese e anno dalla data più vicina
  alla data di creazione del PDF (`creato` in `read_shift_table`; se manca, la
  data di oggi), entro 14 giorni, con quel numero e quel giorno della settimana.
  Se non c'è, o se i giorni non seguono il calendario, restano i soli numeri:
  `Turni <cognome> dal 09 al 15.pdf`.

**App (`app.py`)**
- Barra laterale: si carica il PDF da file o da link Adobe Acrobat. Il link
  viene risolto da `download_adobe_pdf`, che legge il JSON `dc_data` della
  pagina e recupera anche il nome originale del file, usato solo per la
  didascalia. Poi si sceglie il cognome
  (default "Crudele Francesco") e si preme Genera turni. Il PDF viene scritto
  in un file temporaneo solo per la lettura, poi cancellato. Gli errori di
  lettura compaiono come `st.error`.
- Tab *PDF generato*: gli avvisi dell'estrazione in cima, poi anteprima e
  download.
- Tab *Modifica turni*: correzioni **provvisorie**, solo per questa
  elaborazione. Si fanno nella tabella modificabile con "Salva modifiche e
  rigenera PDF", oppure con il form "Aggiungi un nuovo turno". Vivono nella
  sessione e si perdono ricaricando la pagina.
- Indicazioni: al Genera turni `notes_with_labels` con la chiave di
  `llm_settings` (`st.secrets`, dentro `try` perché senza `secrets.toml`
  solleva) e `cached_llm` (`st.cache_data`: in cache solo le risposte
  riuscite, perché gli errori sollevano).
- Tab *Indicazioni*: la fonte delle etichette, poi una tabella con N, Attiva,
  Etichetta (modificabili le ultime due), i turni a cui va e il testo. "Salva
  indicazioni e rigenera PDF" cambia solo etichetta e Attiva; vale per la
  sessione, come Modifica turni.
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
  requirements.txt`. Per il solo parser e il PDF bastano `pdfplumber`, `fpdf2` e
  `uharfbuzz` (`requests` solo per Gemini); la vecchia `fpdf` va tolta (`uv pip uninstall -p
  .venv/bin/python fpdf`) perché usa lo stesso nome di modulo. Si lancia `main.py` da una cartella che contiene il PDF: il
  programma propone tutti i PDF della cartella tranne quelli che iniziano con
  "Turni ", chiede il cognome, stampa avvisi e turni e scrive il PDF nella
  cartella corrente.
- **In locale, app**: dopo i requisiti, `.venv/bin/streamlit run app.py`.
- **Chiavi dei modelli** (facoltative; senza, le etichette sono "Nota N"):
  Groq (console.groq.com → API Keys) e/o Gemini (Google AI Studio), tutte e
  due gratuite. Su Streamlit Cloud: Manage app → Settings → Secrets, una riga
  per chiave, `GROQ_API_KEY = "..."` e `GEMINI_API_KEY = "..."`. In locale per
  l'app: `.streamlit/secrets.toml` con le stesse righe (escluso da git); per la
  CLI le stesse variabili d'ambiente. `LLM_PROVIDERS` dà l'ordine: prima Groq
  (qwen/qwen3.8-27b, openai/gpt-oss-120b, openai/gpt-oss-20b), poi Gemini (gemini-3.6-flash,
  gemini-3.8-flash, gemini-3.5-flash-lite), saltando i fornitori senza chiave,
  con al massimo `LLM_TIMEOUT` (40 s) per modello; al primo errore (503, 429,
  timeout) si passa al successivo. `GROQ_MODEL` / `GEMINI_MODEL` nei Secrets,
  con uno o più nomi separati da virgole, sostituiscono la lista di quel
  fornitore. La risposta resta in cache fino al riavvio dell'app.

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
- 2026-11-13, pulizia bagni dall'orario (0006) su `pdf_turni/`: sett. 47 4
  "Mattina" e 7 "19:00", dal 02 al 08 7 + 7; tutti gli altri PDF con valori e
  avvisi identici al metodo della 0004.
- 2026-11-20, bordo mancante fra orario e lunedì: su `pdf_turni/` cambiano
  solo tre turni, tutti di lunedì e tutti prima persi come "Riposo": sett. 48
  Crudele a Villa Bonelli (09-13 e 16-20), sett. 44 Iodice e dal 02 al 08
  Ricchitelli al Paladisfida Borgia. Tutti gli altri turni sono identici.
- 2026-11-06, nome del file: su 17 PDF di `pdf_turni/` con il periodo nel nome,
  17 uguali. Sett. 44, sett. 45 e sett. 46 (da link Adobe) danno la settimana
  giusta. I PDF sono creati 3-5 giorni prima del lunedì; spostando il
  riferimento di ±14 giorni il risultato non cambia.

- 2026-11-20, PDF generato (0007): una pagina per tutte le prove (sett. 47 e 48,
  Crudele 12-18 ago, Iodice 22-28 gen con 3 turni al giorno, Curci F. 10-16 nov
  con 4 pulizie, un caso con righe a mano); scala da 1,13 (Iodice) a 1,45.
  0,3 s e 26 KB per PDF. `week_period` uguale al nome del file su 18 PDF, anche
  a cavallo d'anno ("dal 29 dicembre 2025 al 4 gennaio 2026").

- 2026-11-27, Groq sulla 49 (piano gratuito): qwen/qwen3.8-27b circa 2 s,
  etichette specifiche e uguali fra una chiamata e l'altra, ma 429 alla terza
  chiamata di fila (limite al minuto); openai/gpt-oss-120b 5-8 s, etichette
  buone, una volta su tre 400 "Failed to validate JSON"; openai/gpt-oss-20b
  sempre 400 "Failed to validate JSON".
- 2026-11-27, Gemini sulla 49 con la chiave vera: gemini-3.6-flash 17-54 s,
  etichette specifiche e una per turno; gemini-3.8-flash 503 (troppo
  traffico); gemini-3.5-flash-lite 1,5-2 s, etichette a volte generiche
  ("Gestisci giardini e parchi"). Le risposte cambiano un po' da una chiamata
  all'altra anche a temperatura 0.
- 2026-11-27, indicazioni (0008) su `pdf_turni/`: sett. 49, 48, 47 5 note
  (2 di pulizia), 44 e 02-08 4-5; nei PDF fino a maggio 2026 solo note ad
  asterisco e legenda. Collegamenti: sulla 49 Crudele ha la nota del Puttilli
  sui 3 turni al Puttilli e quella del Simeone sul giovedì al Chieffi;
  Venanzio quella del Borgia sui 4 Borgia; nella 02-08 Rizzi Salvatore al
  Manzoni (mar 03) non prende la nota del Borgia. Turni di tutte le 359
  persone dei 22 PDF identici a prima. PDF: una pagina ed entro i margini su
  tutto `pdf_turni/` per Crudele, sulle persone di prova e con un'etichetta di
  45 caratteri; 0,3-0,6 s per PDF.

## Limiti e comportamenti noti
- **Indicazioni**: una nota va solo sul primo luogo che nomina con una parola
  del suo nome ("borgia", "puttilli", "simeone"); se lo chiama in un altro modo
  non ha etichette, nemmeno con Gemini, ma il testo c'è sempre in fondo al PDF.
  Una nota il cui soggetto viene dopo un altro luogo ("i giardini di via X
  saranno aperti dall'addetto al Y") va sul luogo sbagliato: si toglie
  l'etichetta nella tab Indicazioni (Attiva). Le note ad asterisco e i pezzi
  staccati della legenda invernale ("2°PASSAGGIO ORE 19:00") restano solo
  testo. A Gemini vanno le indicazioni (che contengono la targa del Doblò) e
  luoghi e orari della tabella, mai i nomi; con la chiave gratuita Google può
  usarli per migliorare i suoi prodotti. Il piano gratuito ha pochi accessi al
  giorno: con un errore (429) restano le etichette "Nota N" e il messaggio
  nella tab, e alla generazione dopo si riprova.
- **PDF generato, testi lunghi**: un luogo che non sta nello spazio si
  rimpicciolisce fino al 75% e poi si accorcia con "…"; nel riquadro della
  striscia "Riposo - <luogo> (chiuso)" diventa "Riposo". Un orario che non è
  `HH:MM-HH:MM` (scritto a mano) compare così com'è e non dà Mattina/Pomeriggio.
  Una riga aggiunta a mano senza giorno non finisce nel PDF.
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
- **Pulizia bagni**: la legenda dice solo quali colori contano, il valore
  viene dall'orario. Una regola scritta con parole nuove (senza "19:00",
  "ripasso", "mattino", "12:00") non viene riconosciuta e le celle di quel
  colore danno l'avviso "colore che non è in legenda". Rimedio: aggiungere la
  parola a `LEGEND_KEYS`. Una barretta con sfumatura molto diversa dalle celle
  (29 dic, viola) dà lo stesso avviso. Altre evidenziazioni nelle righe di
  Giardini del Castello (il verde delle sett. 47 e 02-08) danno lo stesso
  avviso. Un colore di legenda su un turno che comincia dopo mezzogiorno e
  finisce prima delle 19 dà l'avviso "né di mattina né delle 19:00". Tutti
  questi casi si correggono a mano nella tab Modifica turni.
- **Nome del file senza mese**: succede con un PDF senza data di creazione
  elaborato a più di 14 giorni dalla sua settimana, o con giorni che non seguono
  il calendario. I turni non cambiano, si rinomina il file a mano.
- Titolo della pagina, titolo nei metadati e nome del file sono scritti a mano e
  possono sbagliare (sett. 45: "DAL 02/10/2026" invece di novembre; sett. 46:
  metadati "sett 45"). Per il periodo non si usano.
- **Streamlit Cloud dopo un push**: se `app.py` importa qualcosa di nuovo da
  `main.py`, l'app può dare `ImportError` perché il processo tiene il vecchio
  modulo in memoria. Rimedio: Manage app → ⋮ → Reboot app. Il riavvio reinstalla
  le dipendenze e richiede qualche minuto.
- I nomi dei luoghi sono quelli scritti nel PDF, maiuscole comprese ("Permessi
  vari").
- Il cognome si cerca come sottostringa: "Rossi" trova anche "Rossini".
  Conviene scrivere cognome e nome. La CLI chiede almeno 3 caratteri.
- CLI: non permette di correggere i turni, solo di estrarli e generare il PDF.
  Le correzioni si fanno dall'app.
- Tab Modifica turni: le celle lasciate vuote in una riga aggiunta finiscono
  nel PDF come testo vuoto (un turno senza orario ha "—"), le righe del tutto
  vuote si scartano al salvataggio.
- I PDF dei turni (originali e generati) contengono nomi, malattie e permessi
  dei colleghi: non vanno messi nel repo. `.gitignore` esclude `*.pdf`; per le
  prove in locale si tengono in `pdf_turni/`.

## Comandi utili
```bash
# CLI interattiva (scrive il PDF nella cartella corrente)
.venv/bin/python main.py

# Turni di Crudele senza domande (debug no, conferma del file, cognome, Invio finale).
# Da una cartella con un solo PDF da leggere: con più PDF la CLI chiede quale scegliere.
printf 'n\ns\nCrudele\n\n' | /percorso/repo/.venv/bin/python /percorso/repo/main.py

# Nome del file generato per ogni PDF di pdf_turni/
.venv/bin/python -c "
import main, glob
for p in sorted(glob.glob('pdf_turni/*.pdf')):
    try: print(p, '->', main.output_filename(main.read_shift_table(p), 'Crudele'))
    except ValueError as e: print('ERRORE', p, e)"

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

# Colori in legenda e celle colorate di Giardini del Castello (orario, giorno: nome e colore)
.venv/bin/python -c "
import main, sys
t = main.read_shift_table(sys.argv[1]); print(t['legenda'])
for r in t['rows']:
    if r['luogo'] and 'castello' in r['luogo'].lower():
        print(r['orario'], {t['days'][c][0]: (r['celle'][c], r['colori'][c]) for c in t['days'] if r['colori'][c]})" "file.pdf"

# Indicazioni di ogni PDF (P = pulizia, * = ad asterisco) e luogo a cui vanno
.venv/bin/python -c "
import main, glob
for p in sorted(glob.glob('pdf_turni/*.pdf')):
    try: t = main.read_shift_table(p)
    except ValueError as e: print('ERRORE', p, e); continue
    print(p)
    for n in main.link_notes(t):
        print('  ', n['n'], 'P' if n['pulizia'] else '*' if n['asterisco'] else ' ',
              [r['luogo'] for r in n['regole']], n['testo'][:70])"

# Etichette di Gemini per un PDF (chiave nell'ambiente)
GEMINI_API_KEY=... .venv/bin/python -c "
import main, os, sys
notes, msg = main.notes_with_labels(main.read_shift_table(sys.argv[1]), os.environ['GEMINI_API_KEY'])
print(msg); [print(n['n'], n['etichetta'], n['regole']) for n in notes]" "file.pdf"

# App in locale
uv pip install -p .venv/bin/python -r requirements.txt && .venv/bin/streamlit run app.py
```

## Decisioni collegate
- [0008](decisioni/0008-indicazioni-della-settimana.md) — Indicazioni della
  settimana nel PDF: testo intero, etichetta sul primo luogo nominato, Gemini
  facoltativo per riassumere e restringere.
- [0007](decisioni/0007-layout-pdf-generato.md) — Layout del PDF generato:
  striscia della settimana più elenco dei giorni, con fpdf2 e Inter.
- [0006](decisioni/0006-pulizia-bagni-dall-orario.md) — Pulizia bagni: la
  legenda dice quali colori, l'orario del turno dice quale pulizia.
- [0005](decisioni/0005-nome-file-dal-contenuto-del-pdf.md) — Nome del PDF
  generato dai giorni della tabella e dalla data di creazione del PDF.
- [0004](decisioni/0004-pulizia-bagni-dalla-legenda.md) — Pulizia bagni dal
  colore delle celle, con il significato letto dalla legenda; superata dalla
  0006.
- [0003](decisioni/0003-luoghi-dai-bordi-del-pdf.md) — Luogo e orario letti dai
  bordi del PDF, senza `structure.json`.
- [0001](decisioni/0001-struttura-hardcoded-per-indice.md) e
  [0002](decisioni/0002-niente-struttura-di-riserva.md) — mappa per indice in
  `structure.json`, superate dalla 0003.
