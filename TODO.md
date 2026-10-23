# Da fare

Solo azioni aperte. Quando una è fatta si cancella: l'esito va nel README
dell'unità o in una decisione, e la cronaca resta nel commit. Regole in
CONVENZIONI.md, idee non urgenti in BACKLOG.md.

## Documentazione
- [S] Scrivere `README.md` alla radice con le sezioni della Parte C: com'è
  fatto il parser (indici di riga, `structure.json`, fallback in `main.py`),
  il flusso delle correzioni provvisorie e permanenti da Streamlit, come si
  lancia in locale.

## Pulizia
- [S] Togliere `__pycache__/app.cpython-314.pyc` da git e aggiungere
  `__pycache__/` a `.gitignore`.
- [S] Allineare (o togliere) la struttura di fallback in
  `get_hardcoded_structure()` di `main.py`: non corrisponde più a
  `structure.json`.

## Parser
- [M] Decidere se proseguire con `lavori/allineamento-righe-per-contenuto.md`,
  anche solo con la parte degli avvisi al posto del fallback silenzioso a
  "Riposo".
