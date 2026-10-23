# Turnizio Bar.S.A.

## A cosa serve
Dal PDF settimanale "servizio custodia e pulizia" di Bar.S.A. estrae i turni di
una persona (giorno, luogo, orario) e genera un PDF riassuntivo con solo quelli.
Due interfacce sullo stesso parser: l'app Streamlit (`app.py`, deploy da `main`
su Streamlit Cloud) e uno script interattivo da terminale (`main.py`).

## Com'è fatto

**Parser (`main.py`)**
- `read_pdf_tables` legge tutte le tabelle di tutte le pagine con pdfplumber
  (`extract_tables`).
- L'header è la riga, fra le prime tre di ogni tabella, che ha celle tipo
  "lunedì 26". I giorni vanno bene sia con l'accento sia con l'apostrofo
  (`normalize_day_name`). Internamente mercoledì si scrive `mercoledi'`.
- Ogni riga sotto l'header ha un **indice** = riga della tabella − riga
  dell'header − 1. Le righe completamente vuote non producono turni, ma contano
  nell'indice.
- Il significato di ogni indice (luogo, orario) sta in `structure.json`, nella
  forma `{"0": ["Luogo", "HH:MM-HH:MM", ""], ...}`, scritto a mano (decisione
  0001). `get_hardcoded_structure()` lo carica. Non c'è una copia di riserva nel
  codice (decisione 0002): se il file manca o non si legge, solleva un errore.
- Ogni cella che contiene il cognome (sottostringa, senza distinzione di
  maiuscole), in una colonna giorno, diventa un turno con luogo e orario
  dell'indice. Se la cella contiene un orario (`12,00-18,00`, `8:00/14:00`),
  quello sostituisce l'orario della struttura.
- Luoghi con "chiuso/chiusa" diventano "Riposo - <luogo>". Riposo e ferie non
  hanno orario. I giorni dove il cognome non compare diventano "Riposo".
- `write_shifts_to_pdf` genera il PDF con fpdf. Se fra i turni c'è Giardini del
  Castello, aggiunge la colonna "Pulizia bagni", con "No" di default. Il nome del
  file è `Turni <cognome> dal … .pdf`, preso dal nome del PDF di partenza.

**App (`app.py`)**
- Barra laterale: si carica il PDF da file o da link Adobe Acrobat. Il link
  viene risolto da `download_adobe_pdf`, che legge il JSON `dc_data` della
  pagina e recupera anche il nome originale del file. Poi si sceglie il cognome
  (default "Crudele Francesco") e si preme Genera turni.
- Tab *PDF generato*: anteprima e download.
- Tab *Modifica turni*: correzioni **provvisorie**, solo per questa
  elaborazione. Si fanno nella tabella modificabile con "Salva modifiche e
  rigenera PDF", oppure con il form "Aggiungi un nuovo turno". Vivono nella
  sessione e si perdono ricaricando la pagina.
- Tab *Configurazione*: correzioni della **struttura**.
  - "Strumenti debug PDF" › "Analizza righe PDF" mostra, per ogni riga del PDF,
    l'indice che le assegna il parser: serve per capire quale indice correggere.
  - "Mappatura indici PDF": si modifica luogo e orario di ogni indice.
    "Inserisci riga qui" e "Rimuovi riga qui" fanno scalare di uno tutti gli
    indici successivi: è la correzione da usare quando l'azienda aggiunge o
    toglie una riga.
  - "Applica e salva" scrive `structure.json` sul disco del server.
    "Ripristina default" rilegge quel file. "Carica structure.json" importa un
    JSON nella sessione.
  - Per applicare una struttura cambiata ai turni, si preme di nuovo Genera
    turni.
  - Correzione **permanente**: "Scarica JSON per GitHub", poi si sostituisce
    `structure.json` nel repo e si fa commit e push su `main`.

`old/` contiene script vecchi non più usati.

## Come si usa
- **App online**: si apre l'app su Streamlit Cloud, si carica il PDF (o si
  incolla il link Adobe), si scrive il cognome e si scarica il PDF. Se un luogo
  è sbagliato su tutta la tabella, va corretta la struttura (tab
  Configurazione) e poi committata. Se è sbagliato un turno solo, basta la tab
  Modifica turni.
- **In locale, solo parser**: servono `pdfplumber` e `fpdf` (il `.venv` del repo
  ha queste). Si lancia `main.py` da una cartella che contiene il PDF: il
  programma propone i file che iniziano con "servizio custodia", chiede il
  cognome, stampa i turni e scrive il PDF nella cartella corrente.
- **In locale, app**: `pip install -r requirements.txt`, più `poppler-utils`
  di sistema (`packages.txt`, serve a `pdf2image`), poi `streamlit run app.py`.

Dopo una modifica al parser o a `structure.json`, si rigenerano i turni di
Crudele Francesco sull'ultimo PDF e si confrontano a occhio con la tabella
originale.

## Misure

## Limiti e comportamenti noti
- **Riga aggiunta o tolta nel PDF**: tutto quello che sta sotto scala di un
  indice, senza nessun errore visibile (sett. 44: Malattia letta come Ferie).
  Rimedio: "Analizza righe PDF", poi "Inserisci/Rimuovi riga qui" nella tab
  Configurazione, poi commit di `structure.json`. Alternativa allo studio in
  `lavori/allineamento-righe-per-contenuto.md`.
- Un indice che manca in `structure.json` diventa **"Riposo" in silenzio**.
- Gli orari stampati vengono dalla struttura, non dal PDF, salvo un orario
  scritto nella cella stessa. Ai cambi stagionali vanno aggiornati a mano.
- Il cognome si cerca come sottostringa: "Rossi" trova anche "Rossini".
  Conviene scrivere cognome e nome.
- Se `structure.json` manca o è JSON non valido, l'estrazione si ferma con
  `FileNotFoundError` o `RuntimeError`. Non c'è una struttura di riserva.
- Su Streamlit Cloud "Applica e salva" dura fino al prossimo riavvio dell'app.
  Fino ad allora "Ripristina default" rilegge la versione salvata, non quella
  del repo.
- CLI: rispondere "s" a "Sono necessarie modifiche ai turni?" fa terminare lo
  script con `ImportError`, perché `modify_shifts` non esiste più in `main.py`.
  Le modifiche si fanno dall'app.
- I PDF dei turni (originali e generati) contengono nomi, malattie e permessi
  dei colleghi: non vanno messi nel repo.

## Comandi utili
```bash
# CLI interattiva (scrive il PDF nella cartella corrente)
.venv/bin/python main.py

# Righe del PDF con l'indice che gli assegna il parser
.venv/bin/python -c "import main, sys; [print(r['Indice Struttura'], r['Contenuto'][:2]) for r in main.get_raw_pdf_rows(sys.argv[1])]" "file.pdf"

# Controllo che structure.json si carichi
.venv/bin/python -c "import main; print(len(main.get_hardcoded_structure()), 'indici')"

# App in locale
pip install -r requirements.txt && streamlit run app.py
```

## Decisioni collegate
- [0001](decisioni/0001-struttura-hardcoded-per-indice.md) — Significato delle
  righe scritto a mano, per indice di riga.
- [0002](decisioni/0002-niente-struttura-di-riserva.md) — Niente struttura di
  riserva nel codice: `structure.json` è l'unica fonte.
