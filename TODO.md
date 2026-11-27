# Da fare

Solo azioni aperte. Quando una è fatta si cancella: l'esito va nel README
dell'unità o in una decisione, e la cronaca resta nel commit. Regole in
CONVENZIONI.md, idee non urgenti in BACKLOG.md.

- [ ] Prova su Streamlit Cloud dopo il push (S): Settings → Secrets con
  `GROQ_API_KEY = "..."` e `GEMINI_API_KEY = "..."`, poi Manage app → Reboot app (import nuovi da
  `main.py`). Sett. 49: la riga della fonte nella tab Indicazioni dice
  "da groq qwen/qwen3.8-27b" (in locale circa 2 s). Dalla tab Indicazioni cambiare un'etichetta e togliere Attiva a
  un'altra: il PDF rigenerato le segue. Se la fonte dice "Gemini non
  disponibile", il motivo è scritto lì (chiave, modello, limite gratuito).
