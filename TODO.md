# Da fare

Solo azioni aperte. Quando una è fatta si cancella: l'esito va nel README
dell'unità o in una decisione, e la cronaca resta nel commit. Regole in
CONVENZIONI.md, idee non urgenti in BACKLOG.md.

## Verifiche
- [S] Rigenerare i turni di Crudele Francesco sul PDF della sett. 44 e
  confrontarli a occhio con la tabella originale (controllo di `/revisione`
  dopo la rimozione della struttura di riserva, decisione 0002).
- [S] Provare l'app in locale (`.venv/bin/streamlit run app.py`, requisiti
  già installati nel `.venv`) come scritto nel README.
- [S] Su Streamlit Cloud: aggiungere nella tab Modifica turni una riga senza
  orario e senza pulizia, salvare, e controllare che il PDF si rigeneri.

## CLI
- [S] `main.py`: rispondere "s" a "Sono necessarie modifiche ai turni?" va in
  `ImportError` (`modify_shifts` non esiste più). Togliere la domanda o
  rimettere la funzione.

## Parser
- [M] Decidere se proseguire con `lavori/allineamento-righe-per-contenuto.md`,
  anche solo con la parte degli avvisi al posto del fallback silenzioso a
  "Riposo".
