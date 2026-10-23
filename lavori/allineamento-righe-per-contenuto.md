# Allineare le righe del PDF alla struttura per contenuto, non per indice

Stato: **idea non approvata**. Francesco è scettico che funzioni; da valutare
prima di scrivere codice. Taglia stimata: M (tocca solo
`extract_shifts_for_person_hardcoded` in `main.py` e gli avvisi in `app.py`).

## Il problema

`structure.json` associa luogo e orario a un **indice di riga** (riga della
tabella − riga dell'header − 1). Quando l'azienda aggiunge o toglie una riga,
tutto quello che sta sotto scala di uno senza nessun errore. Esempio sett. 44
(26/10–01/11/2026): nuova riga "Giardini Stadio Simeone 14:00-20:00" dopo
Simeone 17:00-20:00 → con la struttura vecchia Palazzo di Città, Cimitero,
Sede, Riposo, Ferie e Malattia risultavano tutti sfalsati (Malattia letta come
"Ferie"). In più gli orari stampati vengono dalla struttura, non dal PDF, e
vanno aggiornati a mano a ogni cambio stagionale (es. commit 6fa3fb8).

Leggere tutto dal PDF senza struttura non basta, verificato sulla sett. 44:
- Il PDF viene da Excel. Le celle davvero unite (Villa Bonelli, Riposo, Ferie,
  Malattia, Cimitero "domenica e festivi") pdfplumber le vede come un'unica
  cella: con `find_tables()` + `table.cells` + `page.crop(bbox)` il luogo
  esce su ogni riga.
- Giardini del Castello, Stadio Puttilli, Stadio Simeone, Palazzo di Città
  invece sono celle separate senza bordi visibili, con il testo nella cella
  centrale: geometricamente le altre righe del blocco sono vuote.
- Etichette di colonna 0 che non sono luoghi ma qualificatori del blocco sopra:
  "sabato e domenica", "domenica", "sabato, domenica e fest. / Feriali",
  "domenica e festivi", "dal Lun. al Sabato".
- Orari su più righe (Castello 08:00-14:00 e 16:00-22:00): la seconda riga ha
  la colonna 1 vuota.
- Formati sporchi in colonna 1: `09:0011:00`, `12,00-18,00`, `08:00-14,00`,
  `14:30-23:30 Iodice Bartolomeo` (nome finito nella cella dell'orario),
  `l. 104`.
- Un secondo header ("Sede Bar.S.A. | turno | lunedi' 26 …") a metà tabella.

## L'idea

Tenere `structure.json` come **modello** (quali righe esistono, in che ordine,
a che luogo appartengono, cosa significano i qualificatori), ma agganciarlo al
PDF per contenuto.

### 1. Allineamento a sequenza (tipo diff)

Per ogni riga del PDF si costruisce una firma: `(etichetta col. 0 normalizzata
o vuota, orario col. 1 normalizzato o vuoto, riga vuota sì/no, è un header sì/no)`.
Per ogni riga della struttura la firma attesa: `(etichetta attesa nel PDF o
vuota, orario atteso o vuoto)`.

Si allineano le due sequenze con `difflib.SequenceMatcher` (o un allineamento
Needleman-Wunsch scritto a mano, ~40 righe, se serve dare punteggi parziali):
- `equal` → riga riconosciuta;
- `replace` 1:1 → stessa riga con orario cambiato (cambio stagionale): si tiene
  il luogo della struttura e si prende l'orario dal PDF;
- `insert` → riga nuova nel PDF, non presente nella struttura → avviso;
- `delete` → riga tolta dal PDF → avviso informativo.

Ancore forti, che non cambiano quasi mai e tengono fermo l'allineamento anche
quando cambiano tanti orari insieme: le etichette dei luoghi in colonna 0, i
due header, le righe vuote di separazione, le etichette Riposo / Ferie /
Malattia / Assente / Permessi vari.

Per rendere il confronto tollerante conviene un punteggio invece dell'uguaglianza
secca: etichetta uguale = molto, orario uguale = abbastanza, orario diverso ma
stessa posizione relativa nel blocco = poco. Con `SequenceMatcher` si ottiene
lo stesso trasformando le firme in token, ma il controllo sui punteggi è minore.

### 2. Orari dal PDF

Dopo l'allineamento: se la colonna 1 della riga ha un orario valido (dopo la
normalizzazione di `,` → `:`, `09:0011:00` → `09:00-11:00`, testo extra
tolto), si stampa quello. Se è vuota (riga di continuazione), si usa l'orario
della riga sopra **dello stesso blocco** o quello della struttura. La struttura
smette di essere la fonte degli orari.

### 3. Avvisi invece del fallback silenzioso a "Riposo"

Oggi una riga senza voce nella struttura diventa "Riposo" senza dire niente.
Al suo posto: una riga `insert` o non riconosciuta **che contiene il nome
cercato** produce un avviso in Streamlit ("riga nuova 14:00-20:00 sotto
Giardini Stadio Simeone, non è nella struttura: luogo proposto Giardini Stadio
Simeone"). Le righe nuove senza il nome cercato si ignorano o si elencano in un
expander. Questo punto vale anche da solo, senza 1 e 2, e Francesco l'ha capito
e non l'ha scartato.

## Perché potrebbe non funzionare (obiezioni da verificare)

- Orari ripetuti nello stesso blocco (Castello 08:00-14:00 ×2, 16:00-22:00 ×2,
  Paladisfida 14:30-23:30 ×2): l'allineamento può scambiare righe uguali. Per
  il luogo non cambia niente (stesso blocco), ma va controllato che non si
  sposti su un blocco vicino.
- Cambio stagionale che cambia **molti** orari insieme più l'aggiunta di righe
  nella stessa settimana: restano solo le etichette come ancore, e le righe
  senza etichetta in mezzo a un blocco possono finire nel posto sbagliato
  all'interno del blocco. Quanto è grave dipende da quante righe ha il blocco.
- Etichetta di colonna 0 che cambia testo (es. "Giardini viale Manzoni-Via Da
  Vinci" riscritto diversamente): serve un confronto fuzzy sulle etichette.
- Righe che cambiano significato senza cambiare forma (stesso orario, luogo
  diverso): nessun allineamento le vede; si vedono solo a occhio.
- Complessità: l'utente deve fidarsi di un meccanismo che non vede. Gli avvisi
  del punto 3 servono anche a questo.

## Come si verifica, prima di adottarlo

1. Raccogliere i PDF delle settimane passate (quanti più possibile, con layout
   diversi) in una cartella fuori dal repo: contengono nomi e malattie, **non
   vanno su git**.
2. Script di confronto: per ogni PDF e per ogni dipendente, turni estratti con
   il metodo attuale (con la `structure.json` giusta per quella settimana, se
   c'è nella storia git) e con il metodo nuovo. Atteso: nessuna differenza
   sulle settimane in cui la struttura era aggiornata.
3. Test negativo: PDF sett. 44 con la `structure.json` **vecchia** (commit
   561041a). Atteso: il metodo nuovo trova la riga Simeone 14:00-20:00 come
   `insert` e dà Crudele lunedì = Malattia; il metodo attuale dà Ferie.
4. Se 2 o 3 falliscono su casi non rari, l'idea si scarta e si tiene solo il
   punto 3 (avvisi).

## Cosa manca

- Decidere se andare avanti (eventualmente solo con il punto 3).
- I PDF storici per la verifica.
